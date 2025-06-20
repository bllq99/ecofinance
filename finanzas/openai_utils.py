from openai import OpenAI
from django.conf import settings

client = OpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

def obtener_recomendaciones(transacciones):
    """
    Envía las transacciones a OpenAI y obtiene recomendaciones.
    """
    # Formatear las transacciones como texto para enviar a la IA
    transacciones_texto = "\n".join([
        f"{t['fecha']} - {t['descripcion']} - {t['categoria']} - {t['tipo']} - ${t['monto']}"
        for t in transacciones
    ])

    prompt = f"""
    Estas son las transacciones del mes:
    {transacciones_texto}

    Por favor, analiza estas transacciones y proporciona recomendaciones para mejorar las finanzas personales. 
    Considera que este mensaje esta saliendo en la app de finanzas personales EcoFinance, por lo que las recomendaciones deben ser claras y concisas.
    Los GASTOS marcados como Aporte al objetivo son aportes a un objetivo de ahorro, por lo que no deben ser considerados como gastos en el analisis.
    """

    try:
        response = client.chat.completions.create(
            model="deepseek/deepseek-r1:free",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        # Extraer el contenido del mensaje de la respuesta
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error al obtener recomendaciones: {str(e)}"