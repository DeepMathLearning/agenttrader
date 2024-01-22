import flet as ft
import os
 

# Global Variables
global_page_height = 700

directorio_actual = os.getcwd()+'/ejecutables'
archivos = os.listdir(directorio_actual)

at_image = ft.Row(
    [
        ft.Image(
            src=f"/icons/agenttrader-1.png",
            width=60,
            height=60,
            fit=ft.ImageFit.CONTAIN,
        )
    ],
    alignment=ft.MainAxisAlignment.CENTER,
)

at_image1 = ft.Row(
    [
        ft.Image(
            src=f"/icons/agenttrader.png",
            width=120,
            height=120,
            fit=ft.ImageFit.CONTAIN,
        )
    ],
)
bg_color = "#25263D"

process = None

# Initial image
img = ft.Container(
    padding=5,
    #bgcolor=ft.colors.BLUE,
    col={"sm": 6, "md": 6, "xl": 6},
    height=global_page_height,
    border_radius=ft.border_radius.all(20),
    image_src="/icons/hermoso-diseno-holograma-criptomonedas.jpg",
    image_fit="cover",
)

# General Functions
def page_conf(page, changetab):
    page.title = "Agent Trader Work Station"
    page.theme_mode="dark"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.scroll = "always"
    page.window_width = 900
    page.window_height = 700
    page.appbar = ft.AppBar(title=at_image, bgcolor=bg_color)
    page.navigation_bar = ft.NavigationBar(
        bgcolor=bg_color,
        selected_index=0,
        on_change=changetab,
        destinations=[
            ft.NavigationDestination(
                icon=ft.icons.COMPUTER,
                label="Conexión con Broker",
            ),
            ft.NavigationDestination(
                icon=ft.icons.ADB_OUTLINED,
                selected_icon=ft.icons.ANDROID,
                label="Mis Bots",
            ),
            ft.NavigationDestination(
                icon=ft.icons.REAL_ESTATE_AGENT_OUTLINED,
                selected_icon=ft.icons.REAL_ESTATE_AGENT,
                label="Cuenta AgentTrader",
            ),
            ft.NavigationDestination(
                icon=ft.icons.FACE_OUTLINED,
                selected_icon=ft.icons.SUPPORT_AGENT,
                label="Asesoria",
            ),
        ],
    )

def app_second_bar(page):
    rail = ft.AppBar(
            title=at_image1,
            leading_width=60,
            bgcolor=bg_color,
            center_title=False,
            actions=[
                ft.IconButton(ft.icons.HOME, on_click=lambda _: page.go("/")),
                
            ],
        )
    return rail


def items(page):
    items = [
        ft.Container(
            content=ft.Text("Selecciona un Broker", size=20),
            alignment=ft.alignment.center,
            padding=5,
        ),
        ft.Container(
            content=ft.ResponsiveRow(
                [
                    ft.Container(
                        ft.Image(
                            src=f"/icons/binance-l.png",
                            height=40,
                            fit=ft.ImageFit.CONTAIN,
                        ),
                        padding=1,
                        col={"sm": 2, "md": 2, "xl": 2},
                    ),
                    ft.Container(
                        ft.OutlinedButton(
                            text="Binance",
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=10),
                            ),
                            on_click=lambda _: page.go("/binance"),
                            height=50,
                        ),
                        col={"sm": 10, "md": 10, "xl": 10},
                    ),
                ]
            ),
            alignment=ft.alignment.center,
        ),
        ft.Container(
            content=ft.ResponsiveRow(
                [
                    ft.Container(
                        ft.Image(
                            src=f"/icons/ib-icon.png",
                            width=120,
                            height=40,
                            fit=ft.ImageFit.CONTAIN,
                        ),
                        padding=1,
                        col={"sm": 2, "md": 2, "xl": 2},
                    ),
                    ft.Container(
                        ft.OutlinedButton(
                            text="Interactive Brokers",
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=10),
                            ),
                            on_click=lambda _: page.go("/ib"),
                            height=50,
                        ),
                        col={"sm": 10, "md": 10, "xl": 10},
                    ),
                ]
            ),
            alignment=ft.alignment.center,
        ),
    ]

    return items

def column_with_alignment(page,align: ft.MainAxisAlignment):
    return ft.Column(
        [
            ft.Container(
                content=ft.Image(
                    src=f"/icons/agenttrader.png",
                    width=200,
                    height=200,
                    fit=ft.ImageFit.CONTAIN,
                ),
                alignment=ft.alignment.center,
            ),
            ft.Container(
                content=ft.Column(items(page), alignment=align, spacing=30),
            ),
        ],
    )






