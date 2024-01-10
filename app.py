import flet as ft
from controls import *
import os
import subprocess
import psutil
from binance_app import BinanceApp
from ib_app import IBApp



class AppAtws(ft.UserControl):
    def __init__(self, page):
        super().__init__()

        # Global Variables
        self.global_page_height = 700
        self.directorio_actual = os.getcwd()+'/ejecutables'
        self.archivos = os.listdir(directorio_actual)
        self.page = page
        self.tab_1 = None 
        self.tab_2 = None
        self.tab_3 = None
        self.tab_4 = None
        self.tab_list = []
        self.output_text = None
        self.color_dropdown= None
        self.cmd = None
        self.all_processes = None
        self.subprocesses = None
        self.num_subprocesses = 0
        self.process = None
        self.binance_app= BinanceApp(self.page)
        self.ib_app = IBApp(self.page)

    def changetab(self, e):
        self.my_index = e.control.selected_index
        self.tab_1.visible = True if self.my_index == 0 else False
        self.tab_2.visible = True if self.my_index == 1 else False
        self.tab_3.visible = True if self.my_index == 2 else False
        self.tab_4.visible = True if self.my_index == 3 else False
        self.page.update()
    
    def button_clicked(self, e):
        self.output_text.value = f"Dropdown value is:  {self.color_dropdown.value}"
        try:
            self.cmd = [directorio_actual + "/" + self.color_dropdown.value]

            if self.process is None:
                # Start the subprocess with subprocess.Popen if it's not running
                self.process = subprocess.Popen(self.cmd)
            else:
                # If it's already running, terminate it
                self.process.terminate()
                self.process.wait()
                self.process = None

        except Exception as e:
            pass

        self.page.update()
    
    def process_runing(self, e):
        # Get the list of all running processes
        self.all_processes = psutil.process_iter()

        # Filter the subprocesses
        self.subprocesses = [
            process for process in self.all_processes if self.process.parent() is not None
        ]

        # Count the number of subprocesses
        self.num_subprocesses = len(self.subprocesses)

        self.output_text.value = f"Number of running subprocesses: {self.subprocesses}"

        self.page.update()
    
    # PAGE CHANGE FUNCTIONS
    def route_change(self, e) -> None:
        #print("Route change:", e.route)

        self.page.views.clear()
        self.page.scroll = "always"

        self.page.views.append(
            ft.View(
                route="/",
                controls=[
                    self.page.appbar,
                    ft.ResponsiveRow(self.tab_list),
                    self.page.navigation_bar,
                ],
                scroll='ALWAYS'
            )
        )
    #########################################################################################   
    # CONFIGURACIÓN DE BINANCE
    #########################################################################################  
        if self.page.route == "/binance":
            self.binance_app.binance_config()
    #########################################################################################   
    # CONFIGURACIÓN CON EL IB O EL TWS DE INTERACTIVE BROKERS
    #########################################################################################    
        if self.page.route == "/ib":
            self.ib_app.ib_config()

    def view_pop(self, e: ft.ViewPopEvent) -> None:
        self.page.views.pop()
        top_view = self.page.views[-1]
        self.page.go(top_view.route)
    
    # Página principal Configuración con el Broker
    def app_tabs(self):
        self.output_text = ft.Text()
        # Obtiene el directorio actual
        submit_btn = ft.ElevatedButton(text="Start", on_click=self.button_clicked)
        submit_btn1 = ft.ElevatedButton(text="Stop", on_click=self.process_runing)
        color_dropdown = ft.Dropdown(
            width=300,
            options=[ft.dropdown.Option(x) for x in archivos],
        )

        self.tab_1 = ft.Column(
            [
                ft.ResponsiveRow(
                    [
                        ft.Container(
                            column_with_alignment(self.page,ft.MainAxisAlignment.CENTER),
                            padding=5,
                            col={"sm": 6, "md": 6, "xl": 6},
                        ),
                        img,
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            expand=True,
        )

        self.tab_2 = ft.Row(
            [
                ft.Text("Selecciona tu bot:", size=30),
                color_dropdown,
                submit_btn,
                submit_btn1,
                self.output_text,
            ],
            visible=False,
        )

        self.tab_3 = ft.Text("Tab 3", size=30, visible=False)
        self.tab_4 = ft.Text("Tab 4", size=30, visible=False)

        self.tab_list = [self.tab_1, self.tab_2, self.tab_3, self.tab_4]

        