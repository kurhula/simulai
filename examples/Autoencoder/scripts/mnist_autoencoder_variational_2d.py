import os
from unittest import TestCase

import numpy as np

from simulai.file import SPFile
from simulai.optimization import Optimizer


def model():
    from simulai.models import AutoencoderVariational
    from simulai.regression import SLFNN, ConvolutionalNetwork

    transpose = False

    n_inputs = 3
    n_outputs = 3

    ### Layers Configurations ####
    ### BEGIN
    encoder_layers = [
        {
            "in_channels": n_inputs,
            "out_channels": 16,
            "kernel_size": 3,
            "stride": 1,
            "padding": 1,
            "after_conv": {"type": "maxpool2d", "kernel_size": 2, "stride": 2},
        },
        {
            "in_channels": 16,
            "out_channels": 32,
            "kernel_size": 3,
            "stride": 1,
            "padding": 1,
            "after_conv": {"type": "maxpool2d", "kernel_size": 2, "stride": 2},
        },
        {
            "in_channels": 32,
            "out_channels": 64,
            "kernel_size": 3,
            "stride": 1,
            "padding": 1,
            "after_conv": {"type": "maxpool2d", "kernel_size": 2, "stride": 2},
        },
        {
            "in_channels": 64,
            "out_channels": 128,
            "kernel_size": 3,
            "stride": 1,
            "padding": 1,
            "after_conv": {"type": "maxpool2d", "kernel_size": 2, "stride": 2},
        },
    ]

    bottleneck_encoder_layers = {
        "input_size": 128,
        "output_size": 16,
        "activation": "identity",
        "name": "bottleneck_encoder",
    }

    bottleneck_decoder_layers = {
        "input_size": 16,
        "output_size": 128,
        "activation": "identity",
        "name": "bottleneck_decoder",
    }

    decoder_layers = [
        {
            "in_channels": 128,
            "out_channels": 64,
            "kernel_size": 3,
            "stride": 1,
            "padding": 1,
            "before_conv": {"type": "upsample", "scale_factor": 2, "mode": "bicubic"},
        },
        {
            "in_channels": 64,
            "out_channels": 32,
            "kernel_size": 3,
            "stride": 1,
            "padding": 1,
            "before_conv": {"type": "upsample", "scale_factor": 2, "mode": "bicubic"},
        },
        {
            "in_channels": 32,
            "out_channels": 16,
            "kernel_size": 3,
            "stride": 1,
            "padding": 1,
            "before_conv": {"type": "upsample", "scale_factor": 2, "mode": "bicubic"},
        },
        {
            "in_channels": 16,
            "out_channels": n_outputs,
            "kernel_size": 3,
            "stride": 1,
            "padding": 1,
            "before_conv": {"type": "upsample", "scale_factor": 2, "mode": "bicubic"},
        },
    ]

    ### END
    ### Layers Configurations ####

    # Instantiating network
    encoder = ConvolutionalNetwork(
        layers=encoder_layers, activations="tanh", case="2d", name="encoder"
    )
    bottleneck_encoder = SLFNN(**bottleneck_encoder_layers)
    bottleneck_decoder = SLFNN(**bottleneck_decoder_layers)
    decoder = ConvolutionalNetwork(
        layers=decoder_layers,
        activations="tanh",
        case="2d",
        transpose=transpose,
        name="decoder",
    )

    autoencoder = AutoencoderVariational(
        encoder=encoder,
        bottleneck_encoder=bottleneck_encoder,
        bottleneck_decoder=bottleneck_decoder,
        decoder=decoder,
        encoder_activation="tanh",
    )

    autoencoder.summary(input_shape=[None, 3, 16, 16])

    print(f"Network has {autoencoder.n_parameters} parameters.")

    return autoencoder


class TestAutoencoder(TestCase):
    def setUp(self) -> None:
        pass

    def test_autoencoder_eval(self):
        data = np.random.rand(1_000, 3, 16, 16)

        autoencoder = model()

        estimated_output = autoencoder.eval(input_data=data)

        assert estimated_output.shape == data.shape

    def test_autoencoder_save_restore(self):
        data = np.random.rand(1_000, 3, 16, 16)

        autoencoder = model()

        saver = SPFile(compact=False)
        saver.write(
            save_dir="/tmp",
            name=f"autoencoder_{id(autoencoder)}",
            model=autoencoder,
            template=model,
        )

        autoencoder_reload = saver.read(
            model_path=os.path.join("/tmp", f"autoencoder_{id(autoencoder)}")
        )

        estimated_output = autoencoder_reload.eval(input_data=data)

        assert estimated_output.shape == data.shape

    def test_autoencoder_train(self):
        data = np.random.rand(1_000, 3, 16, 16)

        lr = 1e-3
        n_epochs = 1_00

        autoencoder = model()

        autoencoder.summary(input_shape=[None, 3, 16, 16])

        optimizer_config = {"lr": lr}
        params = {"lambda_1": 0.0, "lambda_2": 0.0, "use_mean": False, "relative": True}

        optimizer = Optimizer("adam", params=optimizer_config)

        optimizer.fit(
            op=autoencoder,
            input_data=data,
            target_data=data,
            n_epochs=n_epochs,
            loss="vaermse",
            params=params,
        )

        saver = SPFile(compact=False)
        saver.write(
            save_dir="/tmp",
            name="autoencoder_rb_just_test",
            model=autoencoder,
            template=model,
        )

        print(optimizer.loss_states)

    def test_autoencoder_train_tensorboard(self):
        data = np.random.rand(1_000, 3, 16, 16)

        lr = 1e-3
        n_epochs = 10_000

        autoencoder = model()

        autoencoder.summary(input_shape=[None, 3, 16, 16])

        optimizer_config = {"lr": lr}
        params = {"lambda_1": 0.0, "lambda_2": 0.0, "use_mean": False, "relative": True}

        optimizer = Optimizer("adam", params=optimizer_config, summary_writer=True)

        optimizer.fit(
            op=autoencoder,
            input_data=data,
            target_data=data,
            n_epochs=n_epochs,
            loss="vaermse",
            params=params,
            batch_size=100,
        )
