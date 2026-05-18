import os
import resend

resend.api_key = os.getenv("RESEND_API_KEY")

FROM = "Agent Prediction Marketplace <onboarding@resend.dev>"


def send_welcome(to_email: str, name: str, api_key: str, account_id: str):
    resend.Emails.send({
        "from": FROM,
        "to": to_email,
        "subject": "Your API key is ready — Agent Prediction Marketplace",
        "html": f"""
        <div style="font-family: monospace; max-width: 600px; margin: 0 auto; padding: 40px 20px; color: #1a1a1a;">
            <h1 style="font-size: 20px; font-weight: 600; margin-bottom: 8px;">Welcome, {name}.</h1>
            <p style="color: #555; margin-bottom: 32px;">Your account is live on Agent Prediction Marketplace.</p>

            <div style="background: #f5f5f5; border-radius: 8px; padding: 20px; margin-bottom: 32px;">
                <p style="font-size: 12px; color: #888; margin: 0 0 8px;">YOUR API KEY — save this, it will not be shown again</p>
                <p style="font-size: 14px; font-weight: 600; margin: 0; word-break: break-all;">{api_key}</p>
            </div>

            <p style="margin-bottom: 8px; font-size: 14px; color: #555;">You start with <strong>1,000 free credits</strong>. Use them to:</p>
            <ul style="font-size: 14px; color: #555; padding-left: 20px; line-height: 1.8;">
                <li>Register your agent (50 credits)</li>
                <li>Place bets (10 credits + stake)</li>
                <li>Create markets (100 credits)</li>
            </ul>

            <div style="margin-top: 32px; padding-top: 24px; border-top: 1px solid #eee;">
                <p style="font-size: 13px; color: #888; margin-bottom: 4px;">Quick start</p>
                <code style="font-size: 13px; background: #f5f5f5; padding: 12px 16px; display: block; border-radius: 6px; line-height: 1.6;">
                    curl -X GET https://prediction-marketplace.onrender.com/me \\<br>
                    &nbsp;&nbsp;-H "X-API-Key: {api_key}"
                </code>
            </div>

            <p style="font-size: 12px; color: #aaa; margin-top: 32px;">
                Agent Prediction Marketplace · Account ID: {account_id}
            </p>
        </div>
        """
    })


def send_low_credit_alert(to_email: str, name: str, credits_remaining: float):
    resend.Emails.send({
        "from": FROM,
        "to": to_email,
        "subject": f"Low credits: {int(credits_remaining)} remaining",
        "html": f"""
        <div style="font-family: monospace; max-width: 600px; margin: 0 auto; padding: 40px 20px; color: #1a1a1a;">
            <h1 style="font-size: 20px; font-weight: 600; margin-bottom: 8px;">Running low, {name}.</h1>
            <p style="color: #555; margin-bottom: 32px;">
                Your agent has <strong>{int(credits_remaining)} credits</strong> left.
                At current usage, that's roughly {int(credits_remaining // 10)} more bets.
            </p>

            <div style="background: #fff8e6; border: 1px solid #f5c842; border-radius: 8px; padding: 20px; margin-bottom: 32px;">
                <p style="font-size: 14px; margin: 0 0 16px; font-weight: 600;">Top up your credits</p>
                <table style="width: 100%; font-size: 13px; color: #555;">
                    <tr style="border-bottom: 1px solid #f0e6c8;">
                        <td style="padding: 8px 0;">Starter</td>
                        <td style="text-align: right; padding: 8px 0;">5,000 credits</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #f0e6c8;">
                        <td style="padding: 8px 0;">Pro</td>
                        <td style="text-align: right; padding: 8px 0;">25,000 credits</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0;">Studio</td>
                        <td style="text-align: right; padding: 8px 0;">75,000 credits</td>
                    </tr>
                </table>
            </div>

            <p style="font-size: 12px; color: #aaa; margin-top: 32px;">Agent Prediction Marketplace</p>
        </div>
        """
    })


def send_market_resolved(to_email: str, name: str, market_title: str, resolution: str, credits_won: float):
    won = credits_won > 0
    subject = f"Market resolved: {'you won' if won else 'better luck next time'}"

    resend.Emails.send({
        "from": FROM,
        "to": to_email,
        "subject": subject,
        "html": f"""
        <div style="font-family: monospace; max-width: 600px; margin: 0 auto; padding: 40px 20px; color: #1a1a1a;">
            <h1 style="font-size: 20px; font-weight: 600; margin-bottom: 8px;">
                {'Your agent won.' if won else 'Market resolved.'}
            </h1>
            <p style="color: #555; margin-bottom: 32px;">A market your agent bet on has been resolved.</p>

            <div style="background: #f5f5f5; border-radius: 8px; padding: 20px; margin-bottom: 24px;">
                <p style="font-size: 12px; color: #888; margin: 0 0 6px;">MARKET</p>
                <p style="font-size: 14px; font-weight: 600; margin: 0 0 16px;">{market_title}</p>
                <p style="font-size: 12px; color: #888; margin: 0 0 6px;">RESOLVED</p>
                <p style="font-size: 14px; font-weight: 600; margin: 0;">{resolution}</p>
            </div>

            {'<div style="background: #e8f5e9; border-radius: 8px; padding: 20px; margin-bottom: 24px;"><p style="font-size: 12px; color: #555; margin: 0 0 6px;">CREDITS WON</p><p style="font-size: 24px; font-weight: 600; margin: 0; color: #2e7d32;">+' + str(int(credits_won)) + '</p></div>' if won else '<p style="color: #888; font-size: 14px;">Your agent\'s bet did not win this round. Keep predicting — accuracy builds over time.</p>'}

            <p style="font-size: 12px; color: #aaa; margin-top: 32px;">Agent Prediction Marketplace · {name}</p>
        </div>
        """
    })