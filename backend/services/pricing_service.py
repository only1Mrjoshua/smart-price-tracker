from backend.db import get_db
from backend.utils.time import utc_now
from backend.utils.ids import oid_str

def compute_discount_percent(reference_price: float, current_price: float) -> float:
    if reference_price <= 0:
        return 0.0
    return max(0.0, (reference_price - current_price) / reference_price * 100.0)

async def insert_price_point(tracked_product_id, price: float, currency: str):
    db = get_db()
    await db.price_history.insert_one({
        "tracked_product_id": tracked_product_id,
        "timestamp": utc_now(),
        "price": price,
        "currency": currency,
    })

async def create_notification(user_id, tracked_product_id, message: str, channel: str, status: str):
    db = get_db()
    await db.notifications.insert_one({
        "user_id": user_id,
        "tracked_product_id": tracked_product_id,
        "message": message,
        "channel": channel,  # "email" | "in_app"
        "sent_at": utc_now(),
        "status": status,    # "sent" | "failed"
    })

async def evaluate_alerts_and_notify(tracked_product: dict, latest_price: float, currency: str,
                                     send_email_fn):
    """
    Alert rules:
      - target_price: trigger if latest_price <= target_price
      - discount_threshold: trigger if discount% >= threshold AND tracked_product has reference_price
    """
    db = get_db()
    
    # ========== DEBUG START ==========
    print("\n" + "="*50)
    print("🔍 DEBUG: evaluate_alerts_and_notify called")
    print(f"📦 Product ID: {tracked_product['_id']}")
    print(f"💰 Current price: {latest_price} {currency}")
    print(f"👤 Product user_id: {tracked_product['user_id']}")
    print(f"📝 Product title: {tracked_product.get('title', 'N/A')}")
    print(f"🔗 URL: {tracked_product.get('url', 'N/A')}")
    print("-"*50)
    
    # Find all active alerts for this product
    alerts = db.alerts.find({
        "tracked_product_id": tracked_product["_id"],
        "is_active": True,
    })

    alert_count = 0
    async for alert in alerts:
        alert_count += 1
        print(f"\n📢 ALERT #{alert_count}:")
        print(f"  🆔 Alert ID: {alert['_id']}")
        print(f"  👤 Alert user_id: {alert['user_id']}")
        print(f"  🎯 Target price: {alert.get('target_price')}")
        print(f"  📉 Discount threshold: {alert.get('discount_threshold')}")
        print(f"  🔄 Notify once: {alert.get('notify_once')}")
        print(f"  ✅ Has notified once: {alert.get('has_notified_once')}")
        print(f"  ⚡ Is active: {alert.get('is_active')}")
        
        triggered = False
        reasons = []

        # Check target price
        target_price = alert.get("target_price")
        if target_price is not None:
            comparison = latest_price <= float(target_price)
            print(f"  📊 Target price check: {latest_price} <= {float(target_price)}? {comparison}")
            if comparison:
                triggered = True
                reasons.append(f"Price is now {latest_price:.2f} {currency} (<= target {float(target_price):.2f}).")

        # Check discount threshold
        discount_threshold = alert.get("discount_threshold")
        reference_price = tracked_product.get("reference_price")
        if discount_threshold is not None and reference_price:
            disc = compute_discount_percent(float(reference_price), latest_price)
            print(f"  📊 Discount check: {disc:.1f}% >= {float(discount_threshold):.1f}%? {disc >= float(discount_threshold)}")
            if disc >= float(discount_threshold):
                triggered = True
                reasons.append(f"Discount is {disc:.1f}% (>= {float(discount_threshold):.1f}%).")

        if not triggered:
            print("  ❌ No trigger conditions met")
            continue

        # Check if already notified for once-only alerts
        if alert.get("notify_once") and alert.get("has_notified_once"):
            print("  ⏭️ Already notified once (notify_once=True), skipping")
            continue

        print(f"  ✅ TRIGGERED! Reasons: {reasons}")
        
        # ========== END DEBUG ==========

        # Plain text message for in-app notification
        plain_message = (
            f"Deal alert for '{tracked_product.get('title','(unknown)')}' on {tracked_product.get('platform')}.\n"
            + "\n".join(reasons)
            + f"\nURL: {tracked_product.get('url')}"
        )

        # HTML styled message for email
        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: 'Poppins', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #f0f5f4;
            margin: 0;
            padding: 0;
            line-height: 1.6;
        }}
        .email-container {{
            max-width: 600px;
            margin: 20px auto;
            background: #ffffff;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(24, 24, 24, 0.1);
            border: 1px solid rgba(24, 24, 24, 0.08);
        }}
        .email-header {{
            background: linear-gradient(135deg, #5285e8 0%, #3a75e5 100%);
            padding: 32px 24px;
            text-align: center;
        }}
        .email-header h1 {{
            margin: 0;
            color: #ffffff;
            font-size: 24px;
            font-weight: 600;
            letter-spacing: -0.5px;
        }}
        .email-header p {{
            margin: 8px 0 0;
            color: rgba(255, 255, 255, 0.9);
            font-size: 14px;
        }}
        .email-content {{
            padding: 32px 24px;
        }}
        .product-card {{
            background: #f8faf9;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
            border: 1px solid #e8eceb;
        }}
        .product-title {{
            font-size: 18px;
            font-weight: 600;
            color: #181818;
            margin: 0 0 12px 0;
            line-height: 1.4;
        }}
        .price-tag {{
            background: #ffffff;
            border-radius: 50px;
            padding: 8px 16px;
            display: inline-block;
            margin: 8px 0;
            border: 1px solid #5285e8;
            color: #5285e8;
            font-weight: 600;
        }}
        .reason-item {{
            background: #ffffff;
            border-radius: 8px;
            padding: 12px 16px;
            margin: 8px 0;
            border-left: 4px solid #5285e8;
            box-shadow: 0 2px 8px rgba(24, 24, 24, 0.04);
        }}
        .reason-icon {{
            color: #5285e8;
            margin-right: 8px;
        }}
        .details-table {{
            width: 100%;
            margin: 20px 0;
            border-collapse: collapse;
        }}
        .details-table td {{
            padding: 12px 0;
            border-bottom: 1px solid #e8eceb;
        }}
        .details-table td:first-child {{
            color: #5a6361;
            font-weight: 500;
            width: 120px;
        }}
        .details-table td:last-child {{
            color: #181818;
            font-weight: 600;
        }}
        .button {{
            display: inline-block;
            background: #5285e8;
            color: #ffffff;
            text-decoration: none;
            padding: 14px 28px;
            border-radius: 50px;
            font-weight: 600;
            font-size: 14px;
            margin: 16px 0 8px;
            transition: all 0.25s ease;
            box-shadow: 0 4px 12px rgba(82, 133, 232, 0.3);
        }}
        .button:hover {{
            background: #3a75e5;
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(82, 133, 232, 0.4);
        }}
        .footer {{
            background: #f0f5f4;
            padding: 24px;
            text-align: center;
            border-top: 1px solid #e8eceb;
        }}
        .footer p {{
            margin: 4px 0;
            color: #5a6361;
            font-size: 12px;
        }}
        .footer-links {{
            margin-top: 12px;
        }}
        .footer-links a {{
            color: #5285e8;
            text-decoration: none;
            font-size: 12px;
            font-weight: 500;
            margin: 0 8px;
        }}
        .footer-links a:hover {{
            text-decoration: underline;
        }}
        .badge {{
            display: inline-block;
            background: rgba(82, 133, 232, 0.1);
            color: #5285e8;
            padding: 4px 12px;
            border-radius: 50px;
            font-size: 12px;
            font-weight: 600;
            border: 1px solid rgba(82, 133, 232, 0.2);
        }}
        @media (max-width: 480px) {{
            .email-container {{
                margin: 10px;
                border-radius: 12px;
            }}
            .email-header {{
                padding: 24px 16px;
            }}
            .email-content {{
                padding: 24px 16px;
            }}
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="email-header">
            <h1>🎯 Price Alert Triggered!</h1>
            <p>Smart Price Tracker • {tracked_product.get('platform', 'unknown').upper()}</p>
        </div>
        
        <div class="email-content">
            <div class="product-card">
                <h2 class="product-title">{tracked_product.get('title', 'Product')}</h2>
                <div>
                    <span class="badge">Current Price</span>
                    <div class="price-tag">{latest_price:,.0f} {currency}</div>
                </div>
            </div>
            
            <h3 style="color: #181818; margin-bottom: 16px;">Why this alert triggered:</h3>
            
            {''.join([f'''
            <div class="reason-item">
                <span class="reason-icon">✓</span>
                {reason}
            </div>
            ''' for reason in reasons])}
            
            <table class="details-table">
                <tr>
                    <td>Platform:</td>
                    <td>{tracked_product.get('platform', 'unknown').upper()}</td>
                </tr>
                {f'''
                <tr>
                    <td>Target Price:</td>
                    <td>{float(alert.get('target_price')):,.0f} {currency}</td>
                </tr>
                ''' if alert.get('target_price') else ''}
                {f'''
                <tr>
                    <td>Discount:</td>
                    <td>{disc:.1f}% (Threshold: {float(discount_threshold):.1f}%)</td>
                </tr>
                ''' if discount_threshold and reference_price else ''}
                <tr>
                    <td>Time:</td>
                    <td>{utc_now().strftime('%B %d, %Y at %I:%M %p')}</td>
                </tr>
            </table>
            
            <div style="text-align: center;">
                <a href="{tracked_product.get('url')}" class="button" target="_blank">🔗 View Product Page</a>
            </div>
            
            <div style="background: #f8faf9; border-radius: 8px; padding: 16px; margin-top: 24px;">
                <p style="margin: 0 0 8px; color: #5a6361; font-size: 13px;">
                    <strong>📱 Manage your alerts:</strong>
                </p>
                <p style="margin: 0; color: #5a6361; font-size: 13px;">
                    You received this because you set up a price alert on Smart Price Tracker. 
                    You can disable or modify this alert anytime from your dashboard.
                </p>
            </div>
        </div>
        
        <div class="footer">
            <p>© 2026 Smart Price Tracker. All rights reserved.</p>
            <p>Stay updated on your favorite products with real-time price alerts.</p>
            <div class="footer-links">
                <a href="#">Dashboard</a>
                <a href="#">Manage Alerts</a>
                <a href="#">Settings</a>
            </div>
            <p style="margin-top: 12px; font-size: 11px; color: #a0a8a6;">
                If you didn't set up this alert, please ignore this email.
            </p>
        </div>
    </div>
</body>
</html>
        """

        # In-app notification (use plain text)
        try:
            await create_notification(tracked_product["user_id"], tracked_product["_id"], plain_message, "in_app", "sent")
            print(f"  📱 In-app notification created")
        except Exception as e:
            print(f"  ❌ In-app notification failed: {e}")
            pass

        # Email notification with HTML
        user = await db.users.find_one({"_id": tracked_product["user_id"]})
        if user and user.get("email"):
            try:
                # Send HTML email
                send_email_fn(
                    user["email"], 
                    f"🎯 Price Alert: {tracked_product.get('title', 'Product')[:50]}...", 
                    html_message,
                    html=True  # You'll need to update email_service.py to support HTML
                )
                await create_notification(tracked_product["user_id"], tracked_product["_id"], plain_message, "email", "sent")
                print(f"  📧 HTML Email sent to {user['email']}")
            except Exception as e:
                await create_notification(tracked_product["user_id"], tracked_product["_id"], plain_message, "email", "failed")
                print(f"  ❌ Email failed: {e}")

        if alert.get("notify_once"):
            await db.alerts.update_one({"_id": alert["_id"]}, {"$set": {"has_notified_once": True}})
            print(f"  🔄 Alert marked as notified_once")
    
    if alert_count == 0:
        print("📭 No active alerts found for this product")
    
    print("="*50 + "\n")
