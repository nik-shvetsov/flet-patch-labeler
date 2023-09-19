import flet as ft
import os
from glob import glob
import tempfile
from pathlib import Path
import pandas as pd

from PIL import Image
import pyvips
from dotenv import dotenv_values


if os.path.exists(".env"):
    CONFIG = dotenv_values(".env")
    PATCH_SIZE = tuple(map(int, CONFIG['PATCH_SIZE'].strip('()').split(',')))
else:
    PATCH_SIZE = (768, 768)


def get_session_indexes(sess_dict):
    return len([v for v in sess_dict.values() if v != '']), len(sess_dict.values())

def main(page):
    page.title = "Patch labeling interface"

    def on_setup_start():
        page.session.set("current_idx", 0)
        page.session.set("current_dict_state", pd.read_csv(page.session.get("rfile_path"), na_filter=False).set_index('PID')['LABEL'].to_dict())
        done_idx, total_idx = get_session_indexes(page.session.get("current_dict_state"))
        page.session.set("done_idx", done_idx)
        page.session.set("total_idx", total_idx)
        
        
        ### Remove initial controls
        upd_controls = [ctrl for i, ctrl in enumerate(page.controls) if type(page.controls[i]) == ft.TextField]
        upd_controls.append(ft.Divider(height=9, thickness=3, color="white"))
        
        ### Set initial values
        page.session.set("wsi_patches", list(page.session.get("current_dict_state").keys()))
        page.session.set("current_patch_path", generate_patch_tmpfile(page.session.get("wsi_patches")[page.session.get("current_idx")]))

        ### Add new controls
        img_canvas = ft.Image(
            src=page.session.get("current_patch_path"),
            width=500,
            height=500,
            fit=ft.ImageFit.CONTAIN,
        )
        img_canvas.data = "id_img_canvas"

        pb_bar = ft.ProgressBar(
            width=500, height=17, value=page.session.get("done_idx")/page.session.get("total_idx")
        )
        pb_bar.data = "id_pb_bar"

        anno_field = ft.TextField(
            label=None,
            read_only=False,
            autofocus=True,
            hint_text="Enter annotations",
            value=page.session.get("current_dict_state").get(page.session.get("wsi_patches")[page.session.get("current_idx")]),
        )
        anno_field.data = "id_anno_field"

        save_btn = ft.ElevatedButton(
                    "Save results",
                    icon=ft.icons.SIM_CARD_DOWNLOAD,
                    on_click=lambda _: update_csv_with_values(
                        page.session.get("rfile_path"),
                        page.session.get("current_dict_state")
                    ),
        )
        page.controls = upd_controls + [img_canvas, pb_bar, anno_field, save_btn]
        page.update()


    def on_wsi_dir_result(textfield, e):
        textfield.value = e.path if e.path else "Cancelled!"
        textfield.update()
        if e.path:
            page.session.set("wsi_files", sorted(glob(os.path.join(e.path, "R*", "*.svs"))))
            page.session.set("slides_dir", e.path)
            if page.session.get("wsi_files") is not None and page.session.get("rfile_path") is not None:
                if len(page.session.get("wsi_files")) > 0 and os.path.exists(page.session.get("rfile_path")): on_setup_start()

    def on_file_dir_result(textfield, e):
        textfield.value = e.files[0].name if e.files else "Cancelled!"
        textfield.update()
        if e.files:
            page.session.set("rfile_path", e.files[0].path)
            if page.session.get("wsi_files") is not None and page.session.get("rfile_path") is not None:
                if len(page.session.get("wsi_files")) > 0 and os.path.exists(page.session.get("rfile_path")): on_setup_start()

    def update_progress_idx():
        ### Tracks overall progress
        done_idx, total_idx = get_session_indexes(page.session.get("current_dict_state"))
        page.session.set("done_idx", done_idx)
        page.session.set("total_idx", total_idx)

    def update_current_page():
        anno_field = list(filter(lambda ctrl: ctrl.data == 'id_anno_field', page.controls))[0] if len(list(filter(lambda ctrl: ctrl.data == 'id_anno_field', page.controls))) == 1 else None
        pb_bar = list(filter(lambda ctrl: ctrl.data == 'id_pb_bar', page.controls))[0] if len(list(filter(lambda ctrl: ctrl.data == 'id_pb_bar', page.controls))) == 1 else None
        img_canvas = list(filter(lambda ctrl: ctrl.data == 'id_img_canvas', page.controls))[0] if len(list(filter(lambda ctrl: ctrl.data == 'id_img_canvas', page.controls))) == 1 else None        
        if anno_field is not None and pb_bar is not None:
            if (anno_field.value is not None and anno_field.value != '' and anno_field.value.strip()):
                labels_dict = page.session.get("current_dict_state")
                labels_dict[list(labels_dict.keys())[page.session.get("current_idx")]] = anno_field.value.strip()
                page.session.set("current_dict_state", labels_dict)
                update_progress_idx()

    def update_csv_with_values(results_csv_path, session_dict):
        update_current_page()
        df = pd.DataFrame(page.session.get("current_dict_state").items(), columns=["PID", "LABEL"])
        df.to_csv(page.session.get("rfile_path"), index=False)

    def generate_patch_tmpfile(slide_patch_str):
        # R46-0357_UNN357_AP_HEorig_40~0~24779.50797
        slide_name, patch_idx, coords = slide_patch_str.split('~')
        patch_top_left = tuple(map(int, coords.split('.')))
        slide_path = os.path.join(page.session.get("slides_dir"), slide_name.split('_')[0], f'{slide_name}.svs')
        vips_slide = pyvips.Image.new_from_file(slide_path, level=0).extract_band(0, n=3)
        patch = vips_slide.crop(*patch_top_left, *PATCH_SIZE)
        img = Image.fromarray(patch.numpy())

        # tempfile.gettempdir()
        tmp_file_name = tempfile.NamedTemporaryFile().name + '.png'
        img.save(tmp_file_name)
        return tmp_file_name

    ##################################################################
    def on_keyboard(e):
        ### check if labeling controls were initialized
        anno_field = list(filter(lambda ctrl: ctrl.data == 'id_anno_field', page.controls))[0] if len(list(filter(lambda ctrl: ctrl.data == 'id_anno_field', page.controls))) == 1 else None
        pb_bar = list(filter(lambda ctrl: ctrl.data == 'id_pb_bar', page.controls))[0] if len(list(filter(lambda ctrl: ctrl.data == 'id_pb_bar', page.controls))) == 1 else None
        img_canvas = list(filter(lambda ctrl: ctrl.data == 'id_img_canvas', page.controls))[0] if len(list(filter(lambda ctrl: ctrl.data == 'id_img_canvas', page.controls))) == 1 else None        
        if anno_field is None or pb_bar is None or img_canvas is None: return

        
        if (e.key == "Arrow Right" or e.key == "Arrow Left"):
            # set autofocus
            if anno_field is not None:
                anno_field.focus()

            # save label if not empty and update dict
            update_current_page()
                
            # "Arrow Right"
            if e.key == "Arrow Right" and page.session.get("current_idx") < len(page.session.get("current_dict_state").keys()) - 1:
                if page.session.get("current_patch_path") is not None and os.path.exists(page.session.get("current_patch_path")):
                    os.remove(page.session.get("current_patch_path"))

                page.session.set("current_idx", page.session.get("current_idx") + 1)
                anno_field.value = page.session.get("current_dict_state").get(page.session.get("wsi_patches")[page.session.get("current_idx")]).strip()
                page.session.set("current_patch_path", generate_patch_tmpfile(page.session.get("wsi_patches")[page.session.get("current_idx")]))
                img_canvas.src = page.session.get("current_patch_path")
                

            # "Arrow Left"
            elif e.key == "Arrow Left" and page.session.get("current_idx") > 0:
                if page.session.get("current_patch_path") is not None and os.path.exists(page.session.get("current_patch_path")):
                    os.remove(page.session.get("current_patch_path"))
            
                page.session.set("current_idx", page.session.get("current_idx") - 1)
                anno_field.value = page.session.get("current_dict_state").get(page.session.get("wsi_patches")[page.session.get("current_idx")]).strip()
                page.session.set("current_patch_path", generate_patch_tmpfile(page.session.get("wsi_patches")[page.session.get("current_idx")]))
                img_canvas.src = page.session.get("current_patch_path")
                            
            pb_bar.value = page.session.get("done_idx") / page.session.get("total_idx")
            page.update()

    ##################################################################
    def window_event(e):
        if e.data == "close":
            page.dialog = confirm_dialog
            confirm_dialog.open = True
            page.update()
    
    def yes_click(e):
        # also delete tmp file/s?
        page.window_destroy()

    def no_click(e):
        confirm_dialog.open = False
        page.update()

    confirm_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Please confirm"),
        content=ft.Text("Do you really want to exit this app?"),
        actions=[
            ft.ElevatedButton("Yes", on_click=yes_click),
            ft.OutlinedButton("No", on_click=no_click),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    ##################################################################
    ########################### Page setup ###########################
    ##################################################################

    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = page.window_max_width = page.window_min_width = 550
    page.window_height = page.window_max_height = page.window_min_height = 950

    page.window_prevent_close = True
    page.on_window_event = window_event
    page.on_keyboard_event = on_keyboard

    ### Initial components

    ########################## WSI directory 
    wsi_dir_text = ft.Text(value="Select .svs directory (.../Aperio/R46)", color="white", size=20)
    wsi_dir_textfield = ft.TextField(
        label="Selected folder",
        read_only=True,
        value=None,
    )
    wsi_dir_dialog = ft.FilePicker(
        on_result=lambda e: on_wsi_dir_result(wsi_dir_textfield, e)
    )
    page.overlay.append(wsi_dir_dialog)
    wsi_dir_btn = ft.ElevatedButton(
        "Open directory",
        icon=ft.icons.FOLDER_OPEN,
        on_click=lambda _: wsi_dir_dialog.get_directory_path(),
    )

    ########################## Result file
    file_dir_text = ft.Text(value="Choose result file (.csv)", color="white", size=20)
    file_dir_textfield = ft.TextField(
        label="Selected file",
        read_only=True,
        value=None,
    )
    file_dir_dialog = ft.FilePicker(
        on_result=lambda e: on_file_dir_result(file_dir_textfield, e)
    )
    page.overlay.append(file_dir_dialog)
    file_dir_btn = ft.ElevatedButton(
        "Choose file",
        icon=ft.icons.FILE_OPEN,
        on_click=lambda _: file_dir_dialog.pick_files(
            allow_multiple=False,
            allowed_extensions=["csv"],
        ),
    )

    horiz_line = ft.Divider(height=9, thickness=3, color="white")

    ### Vars
    page.session.set("slides_dir", None)
    page.session.set("wsi_files", None)
    page.session.set("rfile_path", None)

    # Initial controls    
    page.controls = [
        wsi_dir_text,
        wsi_dir_textfield,
        wsi_dir_btn,
        horiz_line,
        file_dir_text,
        file_dir_textfield,
        file_dir_btn
    ]
    page.update()

# ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8888)
ft.app(target=main)
