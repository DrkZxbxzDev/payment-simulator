from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, field_validator
from faker import Faker
import random
import re
from datetime import datetime

app = FastAPI(title="Simulador Pasarela de Pago - Portafolio")
fake = Faker()


# ── Modelos ────────────────────────────────────────────────────────────────────

class PaymentRequest(BaseModel):
    card_number: str
    expiry: str       # MM/AA o MM/YYYY
    cvv: str
    amount: float

    @field_validator("card_number")
    @classmethod
    def clean_card_number(cls, v: str) -> str:
        cleaned = re.sub(r"[\s\-]", "", v)
        if not cleaned.isdigit():
            raise ValueError("El número de tarjeta solo debe contener dígitos.")
        return cleaned

    @field_validator("amount")
    @classmethod
    def positive_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("El monto debe ser mayor a cero.")
        return v


# ── Helpers ────────────────────────────────────────────────────────────────────

def luhn_algorithm(card_number: str) -> bool:
    digits = [int(d) for d in card_number]
    if len(digits) < 13:
        return False
    for i in range(len(digits) - 2, -1, -2):
        digits[i] *= 2
        if digits[i] > 9:
            digits[i] -= 9
    return sum(digits) % 10 == 0


def get_card_type(card_number: str) -> str:
    if len(card_number) < 4:
        return "Desconocida"
    prefix2 = card_number[:2]
    prefix4 = int(card_number[:4]) if len(card_number) >= 4 else 0

    if card_number.startswith("4"):
        return "Visa"
    if prefix2 in ("51", "52", "53", "54", "55") or 2221 <= prefix4 <= 2720:
        return "Mastercard"
    if prefix2 in ("34", "37"):
        return "American Express"
    return "Desconocida"


def validate_expiry(expiry: str) -> tuple[bool, str]:
    """Acepta MM/AA o MM/YYYY. Devuelve (válida, mensaje)."""
    parts = expiry.strip().split("/")
    if len(parts) != 2:
        return False, "Formato inválido. Usa MM/AA o MM/YYYY."
    try:
        month = int(parts[0])
        year_raw = int(parts[1])
        year = year_raw + 2000 if year_raw < 100 else year_raw
    except ValueError:
        return False, "Fecha de expiración no numérica."

    if not (1 <= month <= 12):
        return False, "Mes inválido."

    now = datetime.now()
    exp = datetime(year, month, 1)
    # La tarjeta es válida hasta el último día del mes indicado
    if (exp.year, exp.month) < (now.year, now.month):
        return False, "Tarjeta vencida."
    return True, "OK"


def validate_cvv(cvv: str, card_type: str) -> tuple[bool, str]:
    """American Express requiere 4 dígitos; el resto, 3."""
    if not cvv.isdigit():
        return False, "El CVV solo debe contener dígitos."
    expected = 4 if card_type == "American Express" else 3
    if len(cvv) != expected:
        return False, f"CVV inválido para {card_type} (se esperan {expected} dígitos)."
    return True, "OK"


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def home():
    html_content = r"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Simulador Pasarela de Pago</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; }
        .card-badge { transition: opacity .2s; }
        input.error { border-color: #f87171 !important; }
        .spinner { display:none }
        .loading .spinner { display:inline-block; animation: spin .8s linear infinite; }
        .loading .btn-text { display:none }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body class="bg-gray-950 text-white min-h-screen">
    <div class="max-w-2xl mx-auto p-8">
        <h1 class="text-4xl font-bold text-center mb-1 text-emerald-400">
            💳 Simulador Pasarela de Pago
        </h1>
        <p class="text-center text-gray-400 mb-8">Proyecto Portafolio — Sebastián Rodríguez</p>

        <div class="bg-gray-900 rounded-3xl p-8 shadow-2xl border border-gray-800">
            <div id="payment-form" class="space-y-6">

                <!-- Número de tarjeta -->
                <div>
                    <div class="flex justify-between items-center mb-2">
                        <label class="text-sm font-medium">Número de Tarjeta</label>
                        <span id="card-badge" class="card-badge text-xs text-gray-400 font-mono"></span>
                    </div>
                    <input type="text" id="card_number" required inputmode="numeric" maxlength="19"
                           class="w-full bg-gray-800 border border-gray-700 rounded-2xl px-5 py-4 text-lg font-mono focus:outline-none focus:border-emerald-500"
                           placeholder="4242 4242 4242 4242"
                           autocomplete="cc-number">
                    <p id="err-card" class="text-red-400 text-xs mt-1 hidden"></p>
                </div>

                <div class="grid grid-cols-2 gap-6">
                    <!-- Expiración -->
                    <div>
                        <label class="block text-sm font-medium mb-2">Expiración (MM/AA)</label>
                        <input type="text" id="expiry" required placeholder="12/28" maxlength="5"
                               inputmode="numeric"
                               class="w-full bg-gray-800 border border-gray-700 rounded-2xl px-5 py-4 focus:outline-none focus:border-emerald-500"
                               autocomplete="cc-exp">
                        <p id="err-expiry" class="text-red-400 text-xs mt-1 hidden"></p>
                    </div>

                    <!-- CVV -->
                    <div>
                        <label class="block text-sm font-medium mb-2">CVV</label>
                        <input type="password" id="cvv" required maxlength="4" placeholder="•••"
                               inputmode="numeric"
                               class="w-full bg-gray-800 border border-gray-700 rounded-2xl px-5 py-4 focus:outline-none focus:border-emerald-500"
                               autocomplete="cc-csc">
                        <p id="err-cvv" class="text-red-400 text-xs mt-1 hidden"></p>
                    </div>
                </div>

                <!-- Monto -->
                <div>
                    <label class="block text-sm font-medium mb-2">Monto (USD)</label>
                    <div class="relative">
                        <span class="absolute left-5 top-1/2 -translate-y-1/2 text-gray-400">$</span>
                        <input type="number" id="amount" value="99.99" step="0.01" min="0.01" required
                               class="w-full bg-gray-800 border border-gray-700 rounded-2xl pl-9 pr-5 py-4 focus:outline-none focus:border-emerald-500">
                    </div>
                    <p id="err-amount" class="text-red-400 text-xs mt-1 hidden"></p>
                </div>

                <!-- Botón -->
                <button id="pay-btn" onclick="submitPayment()"
                        class="w-full bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 py-4 rounded-2xl font-semibold text-lg transition-all flex items-center justify-center gap-2">
                    <svg class="spinner w-5 h-5 border-2 border-white border-t-transparent rounded-full" viewBox="0 0 24 24"></svg>
                    <span class="btn-text">Procesar Pago</span>
                </button>
            </div>

            <div id="result" class="mt-6 hidden"></div>
        </div>

        <!-- Tarjetas de prueba -->
        <div class="mt-8">
            <button onclick="generateCards()"
                    class="w-full bg-gray-800 hover:bg-gray-700 py-4 rounded-2xl font-medium transition-all">
                🔄 Generar Tarjetas de Prueba
            </button>
            <div id="test-cards" class="mt-4 space-y-3 hidden"></div>
        </div>
    </div>

    <script>
        // ── Formateo en tiempo real ──────────────────────────────────────────

        const cardInput = document.getElementById('card_number');
        const badge = document.getElementById('card-badge');

        cardInput.addEventListener('input', (e) => {
            let v = e.target.value.replace(/\D/g, '').slice(0, 16);
            e.target.value = v.replace(/(.{4})/g, '$1 ').trim();
            badge.textContent = detectType(v);
        });

        document.getElementById('expiry').addEventListener('input', (e) => {
            let v = e.target.value.replace(/\D/g, '').slice(0, 4);
            if (v.length >= 3) v = v.slice(0, 2) + '/' + v.slice(2);
            e.target.value = v;
        });

        function detectType(n) {
            if (!n) return '';
            if (n.startsWith('4')) return '💳 Visa';
            if (['51','52','53','54','55'].some(p => n.startsWith(p))) return '💳 Mastercard';
            const p4 = parseInt(n.slice(0, 4));
            if (p4 >= 2221 && p4 <= 2720) return '💳 Mastercard';
            if (n.startsWith('34') || n.startsWith('37')) return '💳 Amex';
            return '';
        }

        // ── Envío ────────────────────────────────────────────────────────────

        async function submitPayment() {
            clearErrors();
            const btn = document.getElementById('pay-btn');
            btn.disabled = true;
            btn.classList.add('loading');

            const payload = {
                card_number: cardInput.value,
                expiry: document.getElementById('expiry').value,
                cvv: document.getElementById('cvv').value,
                amount: parseFloat(document.getElementById('amount').value)
            };

            try {
                const res = await fetch('/validate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();

                if (res.status === 422 && data.detail) {
                    // Errores de validación de Pydantic
                    data.detail.forEach(err => {
                        const field = err.loc[err.loc.length - 1];
                        showError(field, err.msg);
                    });
                } else {
                    showResult(data);
                }
            } catch {
                showResult({ status: 'error', message: '⚠️ Error de conexión. Intenta de nuevo.' });
            } finally {
                btn.disabled = false;
                btn.classList.remove('loading');
            }
        }

        function showResult(data) {
            const div = document.getElementById('result');
            div.classList.remove('hidden');
            const approved = data.status === 'approved';
            div.innerHTML = `
                <div class="p-6 rounded-2xl text-center ${approved
                    ? 'bg-emerald-900 border border-emerald-500'
                    : 'bg-red-900 border border-red-500'}">
                    <p class="text-xl font-semibold mb-2">${data.message}</p>
                    ${data.transaction_id ? `<p class="text-sm opacity-70 font-mono">ID: ${data.transaction_id}</p>` : ''}
                    ${data.card_type    ? `<p class="text-sm opacity-70 mt-1">${data.card_type} •••• ${data.last4 ?? ''}</p>` : ''}
                </div>`;
        }

        function showError(field, msg) {
            const el = document.getElementById(`err-${field}`);
            const input = document.getElementById(field);
            if (el) { el.textContent = msg; el.classList.remove('hidden'); }
            if (input) input.classList.add('error');
        }

        function clearErrors() {
            document.querySelectorAll('[id^="err-"]').forEach(e => e.classList.add('hidden'));
            document.querySelectorAll('input').forEach(i => i.classList.remove('error'));
            document.getElementById('result').classList.add('hidden');
        }

        // ── Tarjetas de prueba ───────────────────────────────────────────────

        async function generateCards() {
            const res = await fetch('/generate?count=3');
            const cards = await res.json();
            const container = document.getElementById('test-cards');
            container.classList.remove('hidden');
            container.innerHTML = cards.map(c => `
                <div class="bg-gray-800 rounded-2xl p-4 flex items-center justify-between cursor-pointer hover:bg-gray-700 transition-all"
                     onclick="fillCard('${c.number}', '${c.expiry}', '${c.cvv}')">
                    <div>
                        <p class="font-mono text-sm">${c.number.replace(/(.{4})/g,'$1 ').trim()}</p>
                        <p class="text-xs text-gray-400 mt-1">Vence ${c.expiry} · CVV ${c.cvv} · ${c.type}</p>
                    </div>
                    <span class="text-emerald-400 text-sm">Usar →</span>
                </div>`).join('');
        }

        function fillCard(number, expiry, cvv) {
            cardInput.value = number.replace(/(.{4})/g, '$1 ').trim();
            badge.textContent = detectType(number.replace(/\s/g,''));
            document.getElementById('expiry').value = expiry;
            document.getElementById('cvv').value = cvv;
        }
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)


@app.post("/validate")
async def validate_card(req: PaymentRequest):
    card_number = req.card_number  # ya limpio gracias al validator
    card_type = get_card_type(card_number)

    # 1. Luhn
    if not luhn_algorithm(card_number):
        return JSONResponse({"status": "rejected", "message": "❌ Tarjeta inválida (falló Luhn)"}, status_code=200)

    # 2. Expiración
    exp_ok, exp_msg = validate_expiry(req.expiry)
    if not exp_ok:
        return JSONResponse({"status": "rejected", "message": f"❌ {exp_msg}"}, status_code=200)

    # 3. CVV
    cvv_ok, cvv_msg = validate_cvv(req.cvv, card_type)
    if not cvv_ok:
        return JSONResponse({"status": "rejected", "message": f"❌ {cvv_msg}"}, status_code=200)

    # 4. Simulación banco emisor
    success_rate = 0.88 if card_type in ("Visa", "Mastercard") else 0.75
    if random.random() < success_rate:
        return JSONResponse({
            "status": "approved",
            "message": f"✅ Pago aprobado por ${req.amount:,.2f}",
            "card_type": card_type,
            "last4": card_number[-4:],
            "transaction_id": fake.uuid4()[:8].upper()
        })

    return JSONResponse({
        "status": "rejected",
        "message": "❌ Pago rechazado por el banco emisor",
        "card_type": card_type
    })


def generate_mastercard_number() -> str:
    """Genera un número Mastercard que siempre empieza con 51-55 (rango clásico)."""
    while True:
        number = fake.credit_card_number(card_type="mastercard")
        if number[:2] in ("51", "52", "53", "54", "55"):
            return number


@app.get("/generate")
async def generate_cards(count: int = 3):
    cards = []
    for _ in range(count):
        card_type = random.choice(["Visa", "Mastercard", "Amex"])
        if card_type == "Visa":
            number = fake.credit_card_number(card_type="visa")
            cvv = fake.credit_card_security_code(card_type="visa")
        elif card_type == "Mastercard":
            number = generate_mastercard_number()
            cvv = fake.credit_card_security_code(card_type="mastercard")
        else:
            number = fake.credit_card_number(card_type="amex")
            cvv = fake.credit_card_security_code(card_type="amex")

        cards.append({
            "number": number,
            "expiry": fake.credit_card_expire(start="now", end="+4y"),
            "cvv": cvv,
            "type": card_type
        })
    return cards


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)