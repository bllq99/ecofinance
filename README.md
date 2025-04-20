# Ecofinance

Este proyecto es una aplicación web desarrollada con **Django** para gestionar las finanzas personales y establecer objetivos de ahorro. Permite registrar ingresos, gastos y crear objetivos de ahorro con el objetivo de llevar un control eficiente de las finanzas.

## 🚀 Características

- **Dashboard**: Visualiza un resumen de los ingresos, gastos y objetivos de ahorro.
- **Transacciones**: Registra y visualiza los ingresos y gastos.
- **Objetivos de Ahorro**: Crea y rastrea tus objetivos de ahorro con una barra de progreso.

## 📋 Requisitos

Asegúrate de tener lo siguiente antes de empezar:

- **Python 3.8 o superior**: [Descargar Python](https://www.python.org/downloads/)
- **PostgreSQL**: Para almacenar los datos de la base de datos. [Descargar PostgreSQL](https://www.postgresql.org/download/)
- **Git**: Para gestionar el código fuente. [Descargar Git](https://git-scm.com/)

## ⚙️ Instalación

Sigue estos pasos para configurar el proyecto en tu máquina local:

### 1. **Clonar el repositorio**

Primero, clona el repositorio en tu máquina local:

```bash
git clone https://github.com/bllq99/ecofinance.git
cd ecofinance
```

## Crear y activar un entorno virtual

Es recomendable usar un entorno virtual para gestionar las dependencias del proyecto. Ejecuta los siguientes comandos para crear y activar el entorno:

```bash
    python -m venv venv
    # En Windows
    venv\Scripts\activate
    # En macOS/Linux
    source venv/bin/activate
```

## Instalar dependencias 

```bash
    pip install -r requirements.txt
```

## Configurar las variables de entorno

```bash
    # Archivo .env
    DATABASE_URL=postgres://usuario:contraseña@localhost:5432/finanzas_db
    SECRET_KEY=tu_clave_secreta
    DEBUG=True
```

DATABASE_URL: Asegúrate de reemplazar usuario, contraseña y finanzas_db por las credenciales correctas de tu base de datos PostgreSQL.

SECRET_KEY: Genera una clave secreta única para tu aplicación Django (puedes usar django.core.management.utils.get_random_secret_key() para obtener una clave).

DEBUG: Deja en True durante el desarrollo, pero cambia a False en producción.

## Configurar la base de datos
Crea una base de datos en PostgreSQL llamada finanzas_db (o el nombre que hayas configurado en el archivo .env), si aún no la has creado:

```bash
    psql -U postgres
    CREATE DATABASE finanzas_db;
```
### Realizar las migraciones de la base de datos
Una vez configurada la base de datos, ejecuta las migraciones para crear las tablas necesarias:

```bash
    python manage.py migrate
```

## 7. Ejecutar el servidor de desarrollo
Finalmente, ejecuta el servidor de desarrollo:

```bash
    python manage.py migrate
```
