#!/bin/bash
# Remove all ntfy-related code from RSS Aggregator

set -e

echo "Removing ntfy notification system..."

# 1. Delete the ntfy notifier service
rm -f app/services/ntfy_notifier.py
echo "Removed app/services/ntfy_notifier.py"

# 2. Remove ntfy import and usage from refresh_service.py
sed -i '/from app.services.ntfy_notifier import send_ntfy_notification/d' app/services/refresh_service.py
sed -i '/for art in new_articles:/,/await send_ntfy_notification/d' app/services/refresh_service.py
# This removes the for-loop block. More precise: remove lines between for loop and its closing.
# Alternatively, use a more robust approach:
perl -i -0777 -pe 's/            # Send notifications for new articles\n            for art in new_articles:\n                await send_ntfy_notification\(\n                    title=art\["title"\],\n                    message=art\["summary"\]\[:200\],\n                    link=art\["link"\]\n                \n//' app/services/refresh_service.py
echo "Removed ntfy calls from refresh_service.py"

# 3. Remove ntfy fields from config.py
sed -i '/ntfy_topic:/d' app/config.py
sed -i '/ntfy_url:/d' app/config.py
echo "Removed ntfy settings from config.py"

# 4. Remove ntfy environment variables from .env.example
sed -i '/NTFY_TOPIC/d' .env.example
sed -i '/NTFY_URL/d' .env.example
echo "Removed ntfy vars from .env.example"

# 5. Remove ntfy environment variables from compose.yaml
sed -i '/NTFY_TOPIC/d' compose.yaml
sed -i '/NTFY_URL/d' compose.yaml
echo "Removed ntfy env vars from compose.yaml"

echo "ntfy removal complete."
echo "Now run: docker compose down && docker compose up --build -d"
