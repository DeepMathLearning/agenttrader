import flet as ft
from controls import *

def ib_config(page):
    page.views.append(
                ft.View(
                    route="/ib",
                    controls=[
                        app_second_bar(page),
                        ft.ResponsiveRow(
                            [
                                ft.Container(col={"sm": 2, "md": 2, "xl": 2}),
                                ft.Container(
                                    ft.Column(
                                        [
                                            ft.Container(
                                                content=ft.Image(
                                                    src=f"/icons/ibks1.png",
                                                    # width=100,
                                                    height=100,
                                                    fit=ft.ImageFit.CONTAIN,
                                                ),
                                                alignment=ft.alignment.center,
                                                padding=10
                                            ),
                                            ft.Container(
                                                content=ft.Text(value="Configure el IB Gateway o TWS", size=16),
                                                alignment=ft.alignment.center,
                                                padding=10
                                            ),
                                            ft.Container(
                                                content=ft.ResponsiveRow(
                                                    [
                                                        ft.Container(
                                                            content=ft.TextField(
                                                                                    label="DIRECCIÓN IP", 
                                                                                    password=False, 
                                                                                    can_reveal_password=True,
                                                                                    value="0.0.0.0",
                                                                                ),
                                                            alignment=ft.alignment.center,
                                                            col={"sm": 6, "md": 6, "xl": 6}
                                                        ),
                                                        ft.Container(
                                                            content=ft.TextField(
                                                                                    label="PUERTO", 
                                                                                    password=False, 
                                                                                    can_reveal_password=True,
                                                                                    value="7446",
                                                                                ),
                                                            alignment=ft.alignment.center,
                                                            col={"sm": 6, "md": 6, "xl": 6}
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
                                        ft.MaterialState.DEFAULT: ft.colors.WHITE,
                                    },
                                    bgcolor={ft.MaterialState.FOCUSED: ft.colors.PINK_200, "": ft.colors.RED},
                                    shape=ft.RoundedRectangleBorder(radius=10),
                                    #color=ft.colors.WHITE
                                ),
                            width=150,
                            height=50

                        ),
                    ],
                    vertical_alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=30,
                    scroll='ALWAYS'
                )
            )

    page.update()