import flet as ft
from controls import *
from app import AppAtws


def main(page: ft.Page) -> None:

    def page_resize(e):
        global global_page_height
        global_page_height = int(page.window_height) - 200
        img.height = global_page_height
        page.update()

    atws = AppAtws(page)
    page_conf(atws.page, atws.changetab)

    atws.page.on_resize = page_resize

        
    atws.app_tabs()

    atws.page.on_route_change = atws.route_change
    atws.page.on_view_pop = atws.view_pop
    atws.page.go(atws.page.route)
    page_resize(None)


ft.app(target=main)


