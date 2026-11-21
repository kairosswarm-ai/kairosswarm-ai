"""Deterministic finance calculators. Every number shown in a video that comes
from math must come from here, never from the language model."""
import math, re


def debt_payoff(balance: float, apr_pct: float, monthly_payment: float, max_months: int = 1200):
    """Fixed monthly payment on a revolving balance."""
    r = apr_pct / 100 / 12
    b, months, interest = float(balance), 0, 0.0
    if monthly_payment <= b * r:
        return {"error": "payment does not cover monthly interest; debt never ends"}
    while b > 0.005 and months < max_months:
        it = b * r
        interest += it
        b = b + it - monthly_payment
        months += 1
    return {"months": months, "years": round(months / 12, 1), "total_interest": round(interest, 2),
            "total_paid": round(balance + interest, 2)}


def minimum_payment_payoff(balance: float, apr_pct: float, pct_of_balance: float = 1.0,
                           floor: float = 25.0, max_months: int = 1200):
    """Minimum payment = interest + pct_of_balance% of balance, with a dollar floor
    (a common US issuer formula)."""
    r = apr_pct / 100 / 12
    b, months, interest = float(balance), 0, 0.0
    while b > 0.005 and months < max_months:
        it = b * r
        pay = max(it + b * pct_of_balance / 100, floor)
        pay = min(pay, b + it)
        interest += it
        b = b + it - pay
        months += 1
    return {"months": months, "years": round(months / 12, 1), "total_interest": round(interest, 2),
            "formula": f"interest + {pct_of_balance}% of balance, min ${floor:.0f}"}


def compound_growth(principal: float, annual_rate_pct: float, years: float,
                    monthly_contribution: float = 0.0):
    r = annual_rate_pct / 100 / 12
    n = int(round(years * 12))
    fv = principal * (1 + r) ** n
    if monthly_contribution:
        fv += monthly_contribution * (((1 + r) ** n - 1) / r) if r else monthly_contribution * n
    contributed = principal + monthly_contribution * n
    return {"future_value": round(fv, 2), "total_contributed": round(contributed, 2),
            "growth": round(fv - contributed, 2)}


def loan_payment(principal: float, apr_pct: float, years: float):
    r = apr_pct / 100 / 12
    n = int(round(years * 12))
    pay = principal / n if r == 0 else principal * r / (1 - (1 + r) ** -n)
    return {"monthly_payment": round(pay, 2), "total_paid": round(pay * n, 2),
            "total_interest": round(pay * n - principal, 2)}


def years_to_double(annual_rate_pct: float):
    r = annual_rate_pct / 100
    return {"years_exact": round(math.log(2) / math.log(1 + r), 1), "rule_of_72": round(72 / annual_rate_pct, 1)}


def arithmetic(expression: str):
    """Plain arithmetic only (+ - * / parentheses, numbers)."""
    allowed = set("0123456789.+-*/() ")
    if not set(expression) <= allowed:
        return {"error": "only plain arithmetic allowed"}
    return {"result": round(eval(expression, {"__builtins__": {}}, {}), 4)}


CALCS = {
    "debt_payoff": debt_payoff,
    "minimum_payment_payoff": minimum_payment_payoff,
    "compound_growth": compound_growth,
    "loan_payment": loan_payment,
    "years_to_double": years_to_double,
    "arithmetic": arithmetic,
}

CALC_DOCS = """Available calculators (call them by name with JSON args):
- debt_payoff(balance, apr_pct, monthly_payment) -> months, years, total_interest, total_paid
- minimum_payment_payoff(balance, apr_pct, pct_of_balance=1.0, floor=25) -> months, years, total_interest
- compound_growth(principal, annual_rate_pct, years, monthly_contribution=0) -> future_value, total_contributed, growth
- loan_payment(principal, apr_pct, years) -> monthly_payment, total_paid, total_interest
- years_to_double(annual_rate_pct) -> years_exact, rule_of_72
- arithmetic(expression) -> result   (plain + - * / only)"""


def _resolve(expr, done):
    """Allow 'c4.future_value - c3.future_value' style references to earlier results."""
    def rep(m):
        r = done.get(m.group(1), {}).get(m.group(2))
        return str(r) if isinstance(r, (int, float)) else m.group(0)
    return re.sub(r"\b(c\d+)\.([a-z_]+)\b", rep, str(expr))


def run_calcs(requests_list):
    out, done = [], {}
    for req in requests_list or []:
        name, args = req.get("name"), dict(req.get("args", {}))
        if name == "arithmetic" and "expression" in args:
            args["expression"] = _resolve(args["expression"], done)
        fn = CALCS.get(name)
        try:
            res = fn(**args) if fn else {"error": f"unknown calculator {name}"}
        except Exception as e:  # bad args from the model
            res = {"error": str(e)}
        out.append({"id": req.get("id"), "name": name, "args": args, "result": res})
        if req.get("id"): done[req["id"]] = res
    return out
