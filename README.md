# 💳 Simulador Pasarela de Pago

Simulador de procesamiento de pagos con tarjeta construido con **FastAPI** y **Python**. Valida números de tarjeta con el algoritmo de Luhn, detecta el tipo de tarjeta (Visa, Mastercard, Amex) y simula la respuesta de un banco emisor.

> Proyecto de portafolio — Sebastián Rodríguez

---

## ✨ Funcionalidades

- ✅ Validación con **algoritmo de Luhn**
- ✅ Detección automática de tipo de tarjeta (Visa, Mastercard, Amex)
- ✅ Validación de **fecha de expiración** y **CVV** (3 dígitos para Visa/MC, 4 para Amex)
- ✅ Simulación de aprobación/rechazo del banco emisor
- ✅ Generador de tarjetas de prueba con autocompletado
- ✅ Formateo automático del número mientras escribes

---

## 🛠️ Tecnologías

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.12 · FastAPI · Uvicorn |
| Validación | Pydantic v2 |
| Frontend | HTML · Tailwind CSS (CDN) · JavaScript vanilla |
| Datos de prueba | Faker |

---

## 🚀 Instalación y uso

```bash
# 1. Clonar el repositorio
git clone https://github.com/DrkZxbxzDev/payment-simulator.git
cd payment-simulator

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Levantar el servidor
uvicorn main:app --reload
```

Abre [http://127.0.0.1:8000](http://127.0.0.1:8000) en tu navegador.

---

## 📡 Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/` | Interfaz web |
| `POST` | `/validate` | Valida y procesa un pago (JSON) |
| `GET` | `/generate?count=3` | Genera tarjetas de prueba |
| `GET` | `/docs` | Documentación interactiva (Swagger UI) |

### Ejemplo de request a `/validate`

```json
{
  "card_number": "5412 3456 7890 1234",
  "expiry": "12/28",
  "cvv": "123",
  "amount": 99.99
}
```

### Respuesta aprobada

```json
{
  "status": "approved",
  "message": "✅ Pago aprobado por $99.99",
  "card_type": "Mastercard",
  "last4": "1234",
  "transaction_id": "A3F9C21B"
}
```

---

## 🧠 Lógica de validación

```
Número de tarjeta
      │
      ▼
  Algoritmo Luhn  ──✗──▶  Rechazado (tarjeta inválida)
      │ ✓
      ▼
  Fecha de expiración  ──✗──▶  Rechazado (tarjeta vencida)
      │ ✓
      ▼
  CVV (longitud según tipo)  ──✗──▶  Rechazado (CVV inválido)
      │ ✓
      ▼
  Simulación banco emisor
  (88% Visa/MC · 75% Amex)
      │
   ┌──┴──┐
approved  rejected
```

---

## 📁 Estructura del proyecto

```
payment-simulator/
├── main.py              # Aplicación FastAPI completa
├── requirements.txt     # Dependencias
└── README.md
```

---

## 📦 requirements.txt

```
fastapi
uvicorn[standard]
faker
pydantic
```

---

## 📄 Licencia

MIT — libre para usar y modificar.