import pyvips
import numpy as np
from glob import glob
import pandas as pd
from dotenv import dotenv_values


CONFIG = dotenv_values(".env")
PATCH_SIZE = tuple(map(int, CONFIG['PATCH_SIZE'].strip('()').split(',')))
WSI_DIR_GLOB = CONFIG['WSI_DIR_GLOB']
PATCH_OFFSET = int(CONFIG['PATCH_OFFSET'])
N_PATCHES_PER_WSI = int(CONFIG['N_PATCHES_PER_WSI'])
N_WSI = int(CONFIG['N_WSI'])
PATCH_MS = {"mean": int(CONFIG['PATCH_MEAN']), "std": int(CONFIG['PATCH_STD'])}
OUTPUT_NAME = CONFIG['OUTPUT_NAME']

def coord_patches_list_gen(
    wsi_list,
    num_patches_per_wsi=N_PATCHES_PER_WSI,
    patch_size=PATCH_SIZE,
    offset=PATCH_OFFSET,
    ms=PATCH_MS,
    verbose=False,
):
    patches_dict = {}
    for slide_path in wsi_list:
        vips_slide = pyvips.Image.new_from_file(slide_path, level=0).extract_band(0, n=3)

        for i in range(num_patches_per_wsi):
            is_high_intensity = True
            while is_high_intensity:
                top_left_coords = (
                    np.random.randint(0 + offset, (vips_slide.width - offset) - patch_size[0]),
                    np.random.randint(0 + offset, (vips_slide.height - offset) - patch_size[1]),
                )
                patch = vips_slide.crop(*top_left_coords, patch_size[0], patch_size[1])
                if verbose:
                    print(f"Patch mean: {patch.avg()}, Patch std: {patch.deviate()}")

                if patch.avg() <= ms["mean"] and patch.deviate() >= ms["std"]:
                    is_high_intensity = False
            patches_dict[f'{vips_slide.get("aperio.Filename")}~{i}~{top_left_coords[0]}.{top_left_coords[1]}'] = ''
    return patches_dict

wsi_list = sorted(glob(WSI_DIR_GLOB))
print (f"Total num of WSIs: {len(wsi_list)}")
gen_list = coord_patches_list_gen(wsi_list[0:N_WSI])

print (f"Total num of keys: {len(gen_list.keys())}")
pd.DataFrame(gen_list.items(), columns=["PID", "LABEL"]).to_csv(OUTPUT_NAME, index=False)