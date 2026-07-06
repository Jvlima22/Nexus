"""
NEXUS Notifier — Envio de email via Gmail SMTP
Requer App Password do Gmail (não a senha normal)
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

GMAIL_USER     = os.getenv("GMAIL_USER", "josulima90@gmail.com")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS", "")   # App Password do Gmail
EMAIL_DEST     = os.getenv("EMAIL_DEST", "josulima90@gmail.com")


def _html(resultado: dict) -> str:
    data    = resultado.get("data", "")[:16].replace("T", " ")
    saldo   = resultado.get("saldo", 0)
    equity  = resultado.get("equity", 0)
    ops     = resultado.get("operacoes", [])
    ignor   = resultado.get("ignorados", [])
    erro    = resultado.get("erro", "")

    cor_eq  = "#22c55e" if equity >= saldo else "#ef4444"

    linhas_ops = ""
    for o in ops:
        cor = "#22c55e" if o["side"] == "BUY" else "#ef4444"
        linhas_ops += f"""
        <tr>
          <td style="padding:6px 10px;border-bottom:1px solid #27272a">{o['symbol']}</td>
          <td style="padding:6px 10px;border-bottom:1px solid #27272a;color:{cor};font-weight:bold">{o['side']}</td>
          <td style="padding:6px 10px;border-bottom:1px solid #27272a">{o['lots']}</td>
          <td style="padding:6px 10px;border-bottom:1px solid #27272a">{o['entry']:.5f}</td>
          <td style="padding:6px 10px;border-bottom:1px solid #27272a;color:#ef4444">{o['sl']:.5f}</td>
          <td style="padding:6px 10px;border-bottom:1px solid #27272a;color:#22c55e">{o['tp']:.5f}</td>
          <td style="padding:6px 10px;border-bottom:1px solid #27272a">1:{o['rr']}</td>
          <td style="padding:6px 10px;border-bottom:1px solid #27272a;color:#a1a1aa">#{o['ticket']}</td>
        </tr>"""

    tabela = f"""
    <table style="width:100%;border-collapse:collapse;font-size:13px;color:#e4e4e7">
      <thead>
        <tr style="background:#18181b;color:#a1a1aa;text-transform:uppercase;font-size:11px">
          <th style="padding:8px 10px;text-align:left">Par</th>
          <th style="padding:8px 10px;text-align:left">Side</th>
          <th style="padding:8px 10px;text-align:left">Lots</th>
          <th style="padding:8px 10px;text-align:left">Entry</th>
          <th style="padding:8px 10px;text-align:left">SL</th>
          <th style="padding:8px 10px;text-align:left">TP</th>
          <th style="padding:8px 10px;text-align:left">RR</th>
          <th style="padding:8px 10px;text-align:left">Ticket</th>
        </tr>
      </thead>
      <tbody>{linhas_ops if linhas_ops else '<tr><td colspan="8" style="padding:12px 10px;color:#71717a">Nenhuma operação aberta nesta sessão.</td></tr>'}</tbody>
    </table>"""

    ignorados_str = ", ".join(ignor) if ignor else "—"
    erro_bloco    = f'<p style="color:#ef4444;margin:12px 0">⛔ Erro: {erro}</p>' if erro else ""

    return f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#09090b;font-family:system-ui,sans-serif;color:#e4e4e7">
  <div style="max-width:680px;margin:0 auto;padding:24px 16px">

    <!-- Header -->
    <div style="background:#18181b;border:1px solid #27272a;border-radius:12px;padding:20px 24px;margin-bottom:16px">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">
        <span style="font-size:20px">⚡</span>
        <span style="font-size:18px;font-weight:700;color:#fff">NEXUS Trader</span>
      </div>
      <div style="color:#71717a;font-size:13px">{data} UTC — Sessão diária</div>
    </div>

    {erro_bloco}

    <!-- Métricas -->
    <div style="display:flex;gap:12px;margin-bottom:16px">
      <div style="flex:1;background:#18181b;border:1px solid #27272a;border-radius:10px;padding:16px">
        <div style="color:#71717a;font-size:11px;text-transform:uppercase;margin-bottom:4px">Saldo</div>
        <div style="font-size:20px;font-weight:700;color:#fff">${saldo:,.2f}</div>
      </div>
      <div style="flex:1;background:#18181b;border:1px solid #27272a;border-radius:10px;padding:16px">
        <div style="color:#71717a;font-size:11px;text-transform:uppercase;margin-bottom:4px">Equity</div>
        <div style="font-size:20px;font-weight:700;color:{cor_eq}">${equity:,.2f}</div>
      </div>
      <div style="flex:1;background:#18181b;border:1px solid #27272a;border-radius:10px;padding:16px">
        <div style="color:#71717a;font-size:11px;text-transform:uppercase;margin-bottom:4px">Operações</div>
        <div style="font-size:20px;font-weight:700;color:#fff">{len(ops)}</div>
      </div>
    </div>

    <!-- Tabela operações -->
    <div style="background:#18181b;border:1px solid #27272a;border-radius:10px;padding:16px;margin-bottom:16px">
      <div style="font-size:14px;font-weight:600;color:#fff;margin-bottom:12px">Operações Abertas</div>
      {tabela}
    </div>

    <!-- Pares ignorados -->
    <div style="background:#18181b;border:1px solid #27272a;border-radius:10px;padding:14px 16px;margin-bottom:16px">
      <span style="color:#71717a;font-size:12px">Pares sem sinal: </span>
      <span style="color:#a1a1aa;font-size:12px">{ignorados_str}</span>
    </div>

    <!-- Footer -->
    <div style="text-align:center;color:#52525b;font-size:11px;padding-top:8px">
      NEXUS Trader Bot — operação autônoma. Não é recomendação de investimento.
    </div>
  </div>
</body>
</html>"""


def enviar_email(resultado: dict) -> bool:
    if not GMAIL_APP_PASS:
        print("⚠️  GMAIL_APP_PASS não configurado no .env — email não enviado.")
        return False

    ops   = resultado.get("operacoes", [])
    erro  = resultado.get("erro", "")
    emoji = "✅" if ops else ("⛔" if erro else "📭")
    data  = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    assunto = f"{emoji} NEXUS Trader — {len(ops)} operação(ões) | {data}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"]    = f"NEXUS Trader <{GMAIL_USER}>"
    msg["To"]      = EMAIL_DEST

    msg.attach(MIMEText(_html(resultado), "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_APP_PASS)
            smtp.send_message(msg)
        print(f"📧 Email enviado para {EMAIL_DEST}")
        return True
    except Exception as e:
        print(f"❌ Falha ao enviar email: {e}")
        return False


if __name__ == "__main__":
    # Teste rápido com dados falsos
    teste = {
        "data": datetime.now(timezone.utc).isoformat(),
        "saldo": 99997.74,
        "equity": 100150.00,
        "operacoes": [
            {"symbol": "EURUSD", "side": "BUY", "lots": 6.06, "entry": 1.14260,
             "sl": 1.13930, "tp": 1.14580, "rr": 1.2, "ticket": 12345},
            {"symbol": "GBPJPY", "side": "BUY", "lots": 3.58, "entry": 215.658,
             "sl": 215.000, "tp": 216.600, "rr": 1.43, "ticket": 12346},
        ],
        "ignorados": ["USDJPY", "USDCHF", "NZDUSD", "USDCAD"],
    }
    enviar_email(teste)
