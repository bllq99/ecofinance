# EcoFinance - Gestión Financiera Personal

![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)

Aplicación web para gestión de finanzas personales con Django y PostgreSQL.

## Características Principales

- 📊 Dashboard financiero interactivo
- 💰 Registro de ingresos y gastos
- 🎯 Objetivos de ahorro con seguimiento
- 📈 Reportes y análisis financieros
- 🔐 Autenticación segura de usuarios

## Requisitos

| Componente    | Versión |
|--------------|---------|
| Python       | 3.8+    |
| PostgreSQL   | 12+     |
| Git          | 2.20+   |

## Instalación

1. Clonar repositorio:
```bash
git clone https://github.com/bllq99/ecofinance.git
cd ecofinance
```
Configurar entorno virtual:

```bash
python -m venv venv
venv\Scripts\activate
```
Instalar dependencias:

```bash
pip install -r requirements.txt
```
## Configuración
Crear config.ini en la raíz del proyecto:

```ini
[database]
engine = django.db.backends.postgresql
name = ecofinance_db
user = tu_usuario
password = tu_contraseña
host = localhost
port = 5432

[settings]
secret_key = tu_clave_secreta
debug = True
allowed_hosts = 127.0.0.1, localhost
```
## Base de Datos
```bash
psql -U postgres -c "CREATE DATABASE ecofinance_db;"
python manage.py migrate
```
### Ejecución
```bash
python manage.py runserver
```
Accede a http://localhost:8000


