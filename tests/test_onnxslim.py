import os
import subprocess
import tempfile

import pytest

from onnxslim import slim
from onnxslim.utils import print_model_info_as_table, summarize_model

MODELZOO_PATH = "/data/modelzoo"
FILENAME = f"{MODELZOO_PATH}/resnet18/resnet18.onnx"


class TestFunctional:
    def __test_command_basic(self, request, in_model_path=FILENAME, out_model_name="resnet18.onnx", arg_str=""):
        with tempfile.TemporaryDirectory() as tempdir:
            summary = summarize_model(slim(in_model_path), request.node.name))
            print_model_info_as_table(summary)
            out_model_path = os.path.join(tempdir, out_model_name)
            slim(in_model_path, out_model_path)
            slim(in_model_path, out_model_path, model_check=True)
            command = f"onnxslim {arg_str} \"{in_model_path}\" \"{out_model_path}\""
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            output = result.stderr.strip()
            # Assert the expected return code
            print(output)
            assert result.returncode == 0
            return in_model_path, out_model_path

    def test_basic(self, request):
        """Test the basic functionality of the slim function."""
        self.__test_command_basic(request)

    def test_input_shape_modification(self, request):
        """Test the modification of input shapes."""
        input_shape_arg_str = "--input-shapes input:1,3,224,224"
        self.__test_command_basic(request, FILENAME, "resnet18.onnx", input_shape_arg_str)

    def test_fp322fp16_conversion(self, request):
        """Test the conversion of an ONNX model from FP32 to FP16 precision."""
        dtype_fp16_arg_str = "--dtype fp16"
        _, out_model_path = self.__test_command_basic(
            request, FILENAME, "resnet18_fp16.onnx", dtype_fp16_arg_str
        )
        dtype_fp32_arg_str = "--dtype fp32"
        self.__test_command_basic(request, out_model_path, "resnet18_fp32.onnx", dtype_fp32_arg_str)


class TestFeature:
    def test_input_shape_modification(self, request):
        """Test the modification of input shapes."""
        summary = summarize_model(slim(FILENAME, input_shapes=["input:1,3,224,224"]), request.node.name)
        print_model_info_as_table(summary)
        assert summary.input_info[0].shape == (1, 3, 224, 224)

        with tempfile.TemporaryDirectory() as tempdir:
            output_name = os.path.join(tempdir, "resnet18.onnx")
            slim(FILENAME, output_name, input_shapes=["input:1,3,224,224"])
            summary = summarize_model(output_name, request.node.name)
            print_model_info_as_table(summary)
            assert summary.input_info[0].shape == (1, 3, 224, 224)

    def test_fp162fp32_conversion(self, request):
        """Test the conversion of an ONNX model from FP16 to FP32 precision."""
        import numpy as np

        with tempfile.TemporaryDirectory() as tempdir:
            output_name = os.path.join(tempdir, "resnet18.onnx")
            slim(FILENAME, output_name, input_shapes=["input:1,3,224,224"], dtype="fp16")
            summary = summarize_model(output_name, request.node.name)
            print_model_info_as_table(summary)
            assert summary.input_info[0].dtype == np.float16
            assert summary.input_info[0].shape == (1, 3, 224, 224)

            slim(output_name, output_name, dtype="fp32")
            summary = summarize_model(output_name, request.node.name)
            print_model_info_as_table(summary)
            assert summary.input_info[0].dtype == np.float32
            assert summary.input_info[0].shape == (1, 3, 224, 224)

    def test_output_modification(self, request):
        """Tests output modification."""
        summary = summarize_model(slim(FILENAME, outputs=["/Flatten_output_0"]), request.node.name)
        print_model_info_as_table(summary)
        assert "/Flatten_output_0" in summary.output_maps

        with tempfile.TemporaryDirectory() as tempdir:
            output_name = os.path.join(tempdir, "resnet18.onnx")
            slim(FILENAME, output_name, outputs=["/Flatten_output_0"])
            summary = summarize_model(output_name, request.node.name)
            print_model_info_as_table(summary)
            assert "/Flatten_output_0" in summary.output_maps

    def test_input_modification(self, request):
        """Tests input modification."""
        summary = summarize_model(
            slim(FILENAME, inputs=["/maxpool/MaxPool_output_0", "/layer1/layer1.0/relu/Relu_output_0"]),
            request.node.name,
        )
        print_model_info_as_table(summary)
        assert "/maxpool/MaxPool_output_0" in summary.input_maps
        assert "/layer1/layer1.0/relu/Relu_output_0" in summary.input_maps

        with tempfile.TemporaryDirectory() as tempdir:
            output_name = os.path.join(tempdir, "resnet18.onnx")
            slim(FILENAME, output_name, inputs=["/maxpool/MaxPool_output_0", "/layer1/layer1.0/relu/Relu_output_0"])
            summary = summarize_model(output_name, request.node.name)
            print_model_info_as_table(summary)
            assert "/maxpool/MaxPool_output_0" in summary.input_maps
            assert "/layer1/layer1.0/relu/Relu_output_0" in summary.input_maps


if __name__ == "__main__":
    pytest.main(
        [
            "-p",
            "no:warnings",
            "-v",
            "tests/test_onnxslim.py",
        ]
    )
