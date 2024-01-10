# This is the header of the desktop application
import flet as ft
from controls import *
import sqlite3

# Connect to data base bank
connect = sqlite3.connect('atws_db.db', check_same_thread=False)
cursor = connect.cursor()

# Crear tabla en el banco de datos
def table_base():
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS binance_api (id INTEGER PRIMARY KEY AUTOINCREMENT, 
        nombre TEXT UNIQUE, api_key TEXT, secret_key TEXT) 
        '''
    )



class BinanceApp(ft.UserControl):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.edit_name = ft.TextField(label='Nombre')
        self.edit_api_key = ft.TextField(label='API KEY')
        self.edit_secret_key = ft.TextField(label='SECRET KEY')

        self.all_data = ft.Column(auto_scroll=True)
        self.api_key = ft.TextField(
                                        label="API KEY", 
                                        password=True, 
                                        can_reveal_password=True
                                    )
        self.secret_key = ft.TextField(
                                        label="SECRET KEY", 
                                        password=True, 
                                        can_reveal_password=True
                                    )
        self.nombre_api = ft.TextField(
                                        label="NOMBRE API"
                                    )
        self.list_row = []

    # Funcion para eliminar dato
    def delete_data(self, x, y):
        cursor.execute(
            "DELETE FROM binance_api WHERE id = ?", [x]
        )
        y.open = False
        # Llamar a la funcion para renderizar
        self.all_data.controls.clear()
        self.renderizar_todos()
        #self.page.update()
    
    # Función para actualizar data
    def actualizar(self, h, x, y, z):
        cursor.execute(
            '''UPDATE binance_api SET nombre = ?, 
            api_key TEXT= ?, 
            secret_key= ?
            WHERE id = ?''', (h, x, y, z)
        )
        connect.commit()

        z.open= False

        self.all_data.controls.clear()
        self.renderizar_todos()
        #self.page.update()

    # READ - Mostrar todos los datos en el banco de datos
    def renderizar_todos(self):
        cursor.execute("SELECT * FROM binance_api")
        connect.commit()
        self.list_row = []
        my_data = cursor.fetchall()

        for dato in my_data:
            
            self.list_row.append(ft.DataRow(
                                cells=[
                                    ft.DataCell(ft.Text(dato[0])),
                                    ft.DataCell(ft.Text(dato[1])),
                                    ft.DataCell(
                                        ft.IconButton(
                                        data=[dato[0], dato[1], dato[2], dato[3]],
                                        icon=ft.icons.SETTINGS_ROUNDED,
                                        icon_color="blue400",
                                        icon_size=20,
                                        tooltip="Editar API",
                                        on_click=self.open_info
                                    )
                                    )
                                ],
                            ))
        
        self.tab_data = ft.DataTable(
                                    columns=[
                                        ft.DataColumn(ft.Text("ID")),
                                        ft.DataColumn(ft.Text("Nombre API")),
                                        ft.DataColumn(ft.Text("Acción"))
                                    ],
                                    rows=self.list_row
                                    )
        self.all_data.controls.append(self.tab_data)
        self.page.update()
        
    def cicle(self):
        self.renderizar_todos()

    # Creando una función para editar los datos
    def open_info(self, e):
        id_user = e.control.data[0]
        self.edit_name.value = e.control.data[1]
        self.edit_api_key.value = e.control.data[2]
        self.edit_secret_key.value = e.control.data[3]

        self.page.update()

        alert_dialog = ft.AlertDialog(
            title=ft.Text(f'Editar API: {self.edit_name.value}'),
            content= ft.Column(
                [self.edit_name,
                 self.edit_api_key,
                 self.edit_secret_key],
                 alignment=ft.alignment.center,
                spacing=30,
            ),
            actions=[
                ft.ElevatedButton(
                    'Eliminar',
                    color='white',
                    bgcolor='red',
                    on_click=lambda e:self.delete_data(id_user, alert_dialog)
                    ),
                ft.ElevatedButton(
                    'Actualizar',
                    on_click=lambda e: self.actualizar(id_user, 
                                                       self.edit_datos.value, 
                                                       alert_dialog)
                )
            ],
            actions_alignment='spaceBetween'
        )
        self.page.dialog = alert_dialog
        alert_dialog.open = True

        # Actualizar pagina
        self.page.update()

    # Crear un dato nuevo dentro del banco de datos
    def add_new_data(self, e):
        cursor.execute("INSERT INTO binance_api (nombre, api_key, secret_key) VALUES (?, ?, ?);", 
                       [self.nombre_api.value, self.api_key.value, self.secret_key.value])
        
        #self.all_data.controls.clear()
        self.renderizar_todos()
        #self.page.update()

    def binance_config(self):
        '''
        Binance configurate page
        '''
        table_base()
        self.renderizar_todos()
        return self.page.views.append(
            ft.View(
                route="/binance",
                controls=[
                    # page.appbar,
                    app_second_bar(self.page),
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
                                                        content=self.nombre_api,
                                                        alignment=ft.alignment.center,
                                                    ),
                                                    ft.Container(
                                                        content=self.api_key,
                                                        alignment=ft.alignment.center,
                                                    ),
                                                    ft.Container(
                                                        content=self.secret_key,
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
                        text="Agregar +", 
                        on_click=self.add_new_data,
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
                    self.all_data
                ],
                vertical_alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=5,
                scroll='ALWAYS'
            )
        )