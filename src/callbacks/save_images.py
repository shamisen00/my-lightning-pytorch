from typing import Optional, Tuple

from lightning.pytorch.callbacks import Callback
import torchvision
from torchvision import transforms
import torch

from src.utils.utils import lab2rgb_torch, de_normalize


class SaveImages(Callback):
    def __init__(
        self,
        lab: bool = True,
        num_samples: int = 16,
        nrow: int = 8,
        padding: int = 2,
        normalize: bool = False,
        norm_range: Optional[Tuple[int, int]] = None,
        scale_each: bool = False,
        pad_value: int = 0,
        log_interval: int = 1,
    ) -> None:
        """
        Args:
            num_samples: Number of images displayed in the grid. Default: ``3``.
            nrow: Number of images displayed in each row of the grid.
                The final grid size is ``(B / nrow, nrow)``. Default: ``8``.
            padding: Amount of padding. Default: ``2``.
            normalize: If ``True``, shift the image to the range (0, 1),
                by the min and max values specified by :attr:`range`. Default: ``False``.
            norm_range: Tuple (min, max) where min and max are numbers,
                then these numbers are used to normalize the image. By default, min and max
                are computed from the tensor.
            scale_each: If ``True``, scale each image in the batch of
                images separately rather than the (min, max) over all images. Default: ``False``.
            pad_value: Value for the padded pixels. Default: ``0``.
        """

        super().__init__()
        self.num_samples = num_samples
        self.nrow = nrow
        self.padding = padding
        self.normalize = normalize
        self.norm_range = norm_range
        self.scale_each = scale_each
        self.pad_value = pad_value
        self.log_interval = log_interval
        self.lab = lab

    def _to_grid(self, images):
        return torchvision.utils.make_grid(
            tensor=images,
            nrow=self.nrow,
            padding=self.padding,
            normalize=self.normalize,
            value_range=self.norm_range,
            scale_each=self.scale_each,
            pad_value=self.pad_value,
        )

    def _to_rgb(self, image):
        image = de_normalize(image)
        image = lab2rgb_torch(image.cpu())
        image = self._to_grid(image)

        return image

    def on_validation_batch_end(self, trainer, pl_module, outputs, batch, batch_idx):
        # log every n batches
        if (batch_idx + 1) % self.log_interval == 0:
            #predictions = (outputs["y_hat"] - torch.min(outputs["y_hat"])) / (torch.max(outputs["y_hat"]) - torch.min(outputs["y_hat"]))

            # input_grid = self._to_grid(batch[0][0])
            # prediction_grid = self._to_grid(outputs["y_hat"][0])
            # target_grid = self._to_grid(outputs["targets"][0])

            # print("input", input_grid[1, :, :])

            input_grid = batch[0][0]
            prediction_grid = outputs["y_hat"][0]
            target_grid = outputs["targets"][0]

            # # Arrange images vertically

            # combined_grid = outputs["targets"][0]

            if self.lab:
                input_grid = self._to_rgb(input_grid)
                prediction_grid = self._to_rgb(prediction_grid)
                target_grid = self._to_rgb(target_grid)

            pl_module.ssim(torch.unsqueeze(prediction_grid, dim=0), torch.unsqueeze(target_grid, dim=0))
            pl_module.log("val/ssim", pl_module.ssim, on_step=False, on_epoch=True, prog_bar=True)

            combined_grid = torch.cat((input_grid, prediction_grid, target_grid), dim=-1).cpu()

            to_pil = transforms.ToPILImage()
            combined_grid = to_pil(combined_grid)

            trainer.logger.experiment.log_image(
                trainer.logger.run_id,
                image=combined_grid,
                artifact_file=f"image{trainer.current_epoch}_{batch_idx}.jpg"
                )
