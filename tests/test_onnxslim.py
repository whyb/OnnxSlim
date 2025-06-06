import os
import subprocess
import tempfile

import numpy as np
import pytest

from onnxslim import slim
from onnxslim.utils import summarize_model

MODELZOO_PATH = "/data/modelzoo"
FILENAME = f"{MODELZOO_PATH}/resnet18/resnet18.onnx"


class TestFunctional:
    def run_basic_test(self, in_model_path, out_model_path, **kwargs):
        check_func = kwargs.get("check_func", None)
        kwargs_api = kwargs.get("api", {})
        kwargs_bash = kwargs.get("bash", "")
        summary = summarize_model(slim(in_model_path, **kwargs_api), in_model_path)
        if check_func:
            check_func(summary)

        slim(in_model_path, out_model_path, **kwargs_api)
        summary = summarize_model(out_model_path, out_model_path)
        if check_func:
            check_func(summary)

        command = f'onnxslim "{in_model_path}" "{out_model_path}" {kwargs_bash}'

        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        output = result.stderr.strip()
        # Assert the expected return code
        print(output)
        assert result.returncode == 0

        summary = summarize_model(out_model_path, out_model_path)
        if check_func:
            check_func(summary)

    def test_basic(self, request):
        with tempfile.TemporaryDirectory() as tempdir:
            out_model_path = os.path.join(tempdir, "resnet18.onnx")
            self.run_basic_test(FILENAME, out_model_path)

    def test_input_shape_modification(self, request):
        def check_func(summary):
            assert summary.input_info[0].shape == (1, 3, 224, 224)

        with tempfile.TemporaryDirectory() as tempdir:
            out_model_path = os.path.join(tempdir, "resnet18.onnx")
            kwargs = {}
            kwargs["bash"] = "--input-shapes input:1,3,224,224"
            kwargs["api"] = {"input_shapes": ["input:1,3,224,224"]}
            kwargs["check_func"] = check_func
            self.run_basic_test(FILENAME, out_model_path, **kwargs)

    def test_input_modification(self, request):
        def check_func(summary):
            assert "/maxpool/MaxPool_output_0" in summary.input_maps
            assert "/layer1/layer1.0/relu/Relu_output_0" in summary.input_maps

        with tempfile.TemporaryDirectory() as tempdir:
            out_model_path = os.path.join(tempdir, "resnet18.onnx")
            kwargs = {}
            kwargs["bash"] = "--inputs /maxpool/MaxPool_output_0 /layer1/layer1.0/relu/Relu_output_0"
            kwargs["api"] = {"inputs": ["/maxpool/MaxPool_output_0", "/layer1/layer1.0/relu/Relu_output_0"]}
            kwargs["check_func"] = check_func
            self.run_basic_test(FILENAME, out_model_path, **kwargs)

    def test_output_modification(self, request):
        def check_func(summary):
            assert "/Flatten_output_0" in summary.output_maps

        with tempfile.TemporaryDirectory() as tempdir:
            out_model_path = os.path.join(tempdir, "resnet18.onnx")
            kwargs = {}
            kwargs["bash"] = "--outputs /Flatten_output_0"
            kwargs["api"] = {"outputs": ["/Flatten_output_0"]}
            kwargs["check_func"] = check_func
            self.run_basic_test(FILENAME, out_model_path, **kwargs)

    def test_dtype_conversion(self, request):
        def check_func_fp16(summary):
            assert summary.input_info[0].dtype == np.float16

        def check_func_fp32(summary):
            assert summary.input_info[0].dtype == np.float32

        with tempfile.TemporaryDirectory() as tempdir:
            out_fp16_model_path = os.path.join(tempdir, "resnet18_fp16.onnx")
            kwargs = {}
            kwargs["bash"] = "--dtype fp16"
            kwargs["api"] = {"dtype": "fp16"}
            kwargs["check_func"] = check_func_fp16
            self.run_basic_test(FILENAME, out_fp16_model_path, **kwargs)

            out_fp32_model_path = os.path.join(tempdir, "resnet18_fp32.onnx")
            kwargs = {}
            kwargs["bash"] = "--dtype fp32"
            kwargs["api"] = {"dtype": "fp32"}
            kwargs["check_func"] = check_func_fp32
            self.run_basic_test(out_fp16_model_path, out_fp32_model_path, **kwargs)

    def test_save_as_external_data(self, request):
        with tempfile.TemporaryDirectory() as tempdir:
            out_model_path = os.path.join(tempdir, "resnet18.onnx")
            kwargs = {}
            kwargs["bash"] = "--save-as-external-data"
            kwargs["api"] = {"save_as_external_data": True}
            self.run_basic_test(FILENAME, out_model_path, **kwargs)
            assert os.path.getsize(out_model_path) < 1e5

    def test_model_check(self, request):
        with tempfile.TemporaryDirectory() as tempdir:
            out_model_path = os.path.join(tempdir, "resnet18.onnx")
            input_data = os.path.join(tempdir, "input.npy")
            test_data = np.random.random((1, 3, 224, 224)).astype(np.float32)
            np.save(input_data, test_data)
            kwargs = {}
            kwargs["bash"] = f"--model-check --model-check-inputs input:{input_data}"
            kwargs["api"] = {"model_check": True, "model_check_inputs": [f"input:{input_data}"]}
            self.run_basic_test(FILENAME, out_model_path, **kwargs)

    def test_inspect(self, request):
        with tempfile.TemporaryDirectory():
            kwargs = {}
            kwargs["bash"] = "--inspect"
            kwargs["api"] = {"inspect": True}
            self.run_basic_test(FILENAME, FILENAME, **kwargs)


if __name__ == "__main__":
    import sys

    sys.exit(
        pytest.main(
            [
                "-p",
                "no:warnings",
                "-v",
                "tests/test_onnxslim.py",
            ]
        )
    )
