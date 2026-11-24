"""Conexión de Django con MySQL / MariaDB (sección 4.2: base de datos relacional MySQL).

- Usa PyMySQL como controlador (no necesita compilar nada en Windows).
- Acepta el MariaDB 10.4 que trae XAMPP. Django 5.2 pide 10.5, pero esta app solo usa
  funciones que 10.4 ya tiene; lo único que se desactiva es INSERT ... RETURNING,
  que llegó en 10.5 (Django vuelve a leer el id con LAST_INSERT_ID, como en MySQL).
- SELECT ... FOR UPDATE (la reserva atómica de la sección 2.7) funciona igual con InnoDB.
"""

import pymysql

# Django revisa la versión del controlador mysqlclient; PyMySQL es compatible.
pymysql.version_info = (2, 2, 1, "final", 0)
pymysql.install_as_MySQLdb()

from django.db.backends.mysql import base, features  # noqa: E402


class DatabaseFeatures(features.DatabaseFeatures):
    @property
    def minimum_database_version(self):
        return (10, 4) if self.connection.mysql_is_mariadb else (8, 0, 11)

    @property
    def can_return_columns_from_insert(self):
        return self.connection.mysql_is_mariadb and self.connection.mysql_version >= (10, 5)

    @property
    def can_return_rows_from_bulk_insert(self):
        return self.can_return_columns_from_insert


class DatabaseWrapper(base.DatabaseWrapper):
    features_class = DatabaseFeatures
