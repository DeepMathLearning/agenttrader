import flet as ft
from controls import *
import os
import subprocess
import psutil
from binance_app import binance_config
from ib_app import ib_config


def main(page: ft.Page) -> None:

    def page_resize(e):
        global global_page_height
        global_page_height = int(page.window_height) - 200
        img.height = global_page_height
        page.update()

    def changetab(e):
        my_index = e.control.selected_index
        tab_1.visible = True if my_index == 0 else False
        tab_2.visible = True if my_index == 1 else False
        tab_3.visible = True if my_index == 2 else False
        tab_4.visible = True if my_index == 3 else False
        page.update()
    
    def button_clicked(e):
        output_text.value = f"Dropdown value is:  {color_dropdown.value}"
        try:
            global process  # Declare process as a global variable
            cmd = [directorio_actual + "/" + color_dropdown.value]

            if process is None:
                # Start the subprocess with subprocess.Popen if it's not running
                process = subprocess.Popen(cmd)
            else:
                # If it's already running, terminate it
                process.terminate()
                process.wait()
                process = None

        except Exception as e:
            pass

        page.update()
    
    def process_runing(e):
        # Get the list of all running processes
        all_processes = psutil.process_iter()

        # Filter the subprocesses
        subprocesses = [
            process for process in all_processes if process.parent() is not None
        ]

        # Count the number of subprocesses
        num_subprocesses = len(subprocesses)

        output_text.value = f"Number of running subprocesses: {subprocesses}"

        page.update()
    
    # PAGE CHANGE FUNCTIONS
    def route_change(e) -> None:
        #print("Route change:", e.route)

        page.views.clear()
        page.scroll = "always"

        page.views.append(
            ft.View(
                route="/",
                controls=[
                    page.appbar,
                    ft.ResponsiveRow(tab_list),
                    page.navigation_bar,
                ],
                scroll='ALWAYS'
            )
        )
    #########################################################################################   
    # CONFIGURACIÓN DE BINANCE
    #########################################################################################  
        if page.route == "/binance":
            binance_config(page)
    #########################################################################################   
    # CONFIGURACIÓN CON EL IB O EL TWS DE INTERACTIVE BROKERS
    #########################################################################################    
        if page.route == "/ib":
            ib_config(page)

    def view_pop(e: ft.ViewPopEvent) -> None:
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page_conf(page, changetab)

    page.on_resize = page_resize

        
    tab_1, tab_2, tab_3, tab_4, output_text, color_dropdown = app_tabs(page,
                                            button_clicked,
                                            process_runing
                                            )

    tab_list = [tab_1, tab_2, tab_3, tab_4]

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go(page.route)
    page_resize(None)


ft.app(target=main)
