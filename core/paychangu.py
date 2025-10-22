# paychangu.py
import requests
import uuid

# 🔑 API Keys
PUB_KEY = "PUB-TEST-WW4IESP3O5ngh9whOMlCEqz18Pos4wl2"
SEC_KEY = "SEC-TEST-nKVP4zxxiVt2sGC5t4gTadn0i6tdxioO"

# Operator IDs
AIRTEL_REF_ID = "20be6c20-adeb-4b5b-a7ba-0769820df4fb"
TNM_REF_ID = "27494cb5-ba9e-437f-a114-4e7a7686bcca"

# ----------------------------
# Verification Function
# ----------------------------
def verify_paychangu_payment(charge_id, payment_type="card"):
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {SEC_KEY}",
    }

    if payment_type == "card":
        url = f"https://api.paychangu.com/charge-card/verify/{charge_id}"
    else:
        url = f"https://api.paychangu.com/mobile-money/payments/{charge_id}/verify"

    try:
        response = requests.get(url, headers=headers, timeout=30)
        return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ----------------------------
# Mobile Money Payment Initialization
# ----------------------------
def mobile_initialize_payment(mobile: str, operator: str, amount: float, email: str):
    operator = operator.lower()
    if operator == "airtel money":
        ref_id = AIRTEL_REF_ID
    elif operator == "tnm mpamba":
        ref_id = TNM_REF_ID
    else:
        return {"init_status": "failed", "init_message": "Invalid operator selected"}

    charge_id = str(uuid.uuid4())
    payload = {
        "charge_id": charge_id,
        "mobile": mobile,
        "mobile_money_operator_ref_id": ref_id,
        "amount": amount,
        "currency": "MWK",
        "email": email,
        "metadata": {"platform": "ikpixels"},
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {SEC_KEY}",
    }

    try:
        response = requests.post(
            "https://api.paychangu.com/mobile-money/payments/initialize",
            json=payload,
            headers=headers,
            timeout=30
        )
        results = response.json()

        if results.get("status") != "success":
            return {
                "init_status": "failed",
                "init_message": results.get("message", "Payment initialization failed"),
            }

        data = results["data"]
        return {
            "init_status": "success",
            "charge_id": data["charge_id"],
            "amount": data.get("amount"),
            "mobile": mobile,
            "operator": data.get("mobile_money", {}).get("name"),
            "message": results.get("message", "Payment initialized successfully")
        }

    except Exception as e:
        return {"init_status": "failed", "init_message": str(e)}

# ----------------------------
# Card Payment Initialization
# ----------------------------
def card_initialize_payment(card_number, expiry, cvv, cardholder_name, amount, currency, email, redirect_url):
    charge_id = f"charge_{uuid.uuid4()}"
    payload = {
        "card_number": card_number,
        "expiry": expiry,
        "cvv": cvv,
        "cardholder_name": cardholder_name,
        "amount": str(amount),
        "currency": currency,
        "email": email,
        "charge_id": charge_id,
        "redirect_url": redirect_url,
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {SEC_KEY}",
    }

    try:
        response = requests.post(
            "https://api.paychangu.com/charge-card/payments",
            json=payload,
            headers=headers,
            timeout=30
        )
        result = response.json()

        if result.get("status") != "success":
            return {
                "init_status": "failed",
                "init_message": result.get("message", "Card payment initialization failed"),
            }

        data = result.get("data", {})
        return {
            "init_status": "success",
            "charge_id": charge_id,
            "amount": amount,
            "email": email,
            "cardholder_name": cardholder_name,
            "message": result.get("message", "Card payment initialized successfully"),
            "redirect_url": redirect_url
        }

    except Exception as e:
        return {"init_status": "failed", "init_message": str(e)}

# ---------------------------------------------------------------------
# 💸 Payout / Withdraw to Mobile
# ---------------------------------------------------------------------
def process_withdrawal(operator_ref_id, phone_number, amount):
    """Send money to mobile user via PayChangu."""
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {SEC_KEY}",
    }

    charge_id = str(uuid.uuid4())
    payload = {
        "amount": float(amount),
        "mobile": phone_number,
        "mobile_money_operator_ref_id": operator_ref_id,
        "currency": "MWK",
        "charge_id": charge_id,
    }

    try:
        response = requests.post(
            "https://api.paychangu.com/mobile-money/payouts/initialize",
            json=payload,
            headers=headers,
            timeout=30
        )
        return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}
