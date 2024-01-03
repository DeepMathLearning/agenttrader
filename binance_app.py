# This is the header of the desktop application
import flet as ft
from controls import *


def binance_config(page):
    '''
    Binance configurate page
    '''
    page.views.append(
        ft.View(
            route="/binance",
            controls=[
                # page.appbar,
                app_second_bar(page),
                ft.ResponsiveRow(
                    [
                        ft.Container(col={"sm": 2, "md": 2, "xl": 2}),
                        ft.Container(
                            ft.Column(
                                [
                                    ft.Container(
                                        content=ft.Image(
                                            src=f"/icons/Binance-logo.png",
                                            # width=250,
                                            height=200,
                                            fit=ft.ImageFit.CONTAIN,
                                        ),
                                        alignment=ft.alignment.center,
                                        #padding=5
                                    ),
                                    ft.Container(
                                        content=ft.Text(value="Ingrese las credenciales de la API de Binance", size=16),
                                        alignment=ft.alignment.center,
                                        padding=5
                                    ),
                                    ft.Container(
                                        content=ft.Column(
                                            [
                                                ft.Container(
                                                    content=ft.TextField(
                                                                            label="API KEY", 
                                                                            password=True, 
                                                                            can_reveal_password=True
                                                                        ),
                                                    alignment=ft.alignment.center,
                                                ),
                                                ft.Container(
                                                    content=ft.TextField(
                                                                            label="SECRET KEY", 
                                                                            password=True, 
                                                                            can_reveal_password=True
                                                                        ),
                                                    alignment=ft.alignment.center,
                                                ),
                                            ],
                                            alignment=ft.alignment.center,
                                            spacing=30,
                                        ),
                                    ),
                                ],
                            ),
                            padding=5,
                            col={"sm": 8, "md": 8, "xl": 8},
                        ),
                    ],
                    alignment=ft.alignment.center,
                ),
                ft.ElevatedButton(
                    text="Aceptar", 
                    on_click=lambda _: page.go("/"),
                    style=ft.ButtonStyle(
                            color={
                                ft.MaterialState.HOVERED: ft.colors.BLUE,
                                ft.MaterialState.FOCUSED: ft.colors.BLUE,
                                ft.MaterialState.DEFAULT: ft.colors.BLACK,
                            },
                            bgcolor={ft.MaterialState.FOCUSED: ft.colors.PINK_200, "": ft.colors.YELLOW},
                            shape=ft.RoundedRectangleBorder(radius=10),
                            #color=ft.colors.WHITE
                        ),
                    width=150,
                    height=50

                ),
            ],
            vertical_alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=5,
            scroll='ALWAYS'
        )
    )