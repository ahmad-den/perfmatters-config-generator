#!/bin/bash

# Perfmatters API Usage Examples
# Replace with your actual domain: https://perfmatters.checkmysite.app

API_URL="https://perfmatters.checkmysite.app"

echo "🚀 Perfmatters API Usage Examples"
echo "=================================="

# 1. Health Check
echo ""
echo "1. Health Check:"
echo "curl -X GET $API_URL/health"
curl -X GET $API_URL/health
echo ""

# 2. Basic Configuration Generation
echo ""
echo "2. Basic Config Generation:"
echo "curl -X POST $API_URL/generate-config \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"plugins\": [\"woocommerce\", \"elementor\"], \"theme\": \"astra\"}' \\"
echo "  --output perfmatters-config.json"

curl -X POST $API_URL/generate-config \
  -H "Content-Type: application/json" \
  -d '{"plugins": ["woocommerce", "elementor"], "theme": "astra"}' \
  --output perfmatters-config.json

echo "✅ Config saved to perfmatters-config.json"
echo ""

# 3. With Domain Analysis (Ad Detection)
echo ""
echo "3. With Domain Analysis (Ad Detection):"
echo "curl -X POST $API_URL/generate-config \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"plugins\": [\"woocommerce\", \"elementor\"], \"theme\": \"astra\", \"domain\": \"https://example.com\", \"analyze_domain\": true}' \\"
echo "  --output perfmatters-config-with-ads.json"

# 4. WordPress CLI Integration Example
echo ""
echo "4. WordPress CLI Integration:"
echo "# Get your WordPress data first:"
echo "wp plugin list --status=active --field=name > active-plugins.txt"
echo "wp theme list --status=active --field=name > active-theme.txt"
echo ""
echo "# Then use with API:"
echo "PLUGINS=\$(wp plugin list --status=active --field=name | jq -R . | jq -s .)"
echo "THEME=\$(wp theme list --status=active --field=name)"
echo "curl -X POST $API_URL/generate-config \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d \"{\\\"plugins\\\": \$PLUGINS, \\\"theme\\\": \\\"\$THEME\\\"}\" \\"
echo "  --output wp-perfmatters-config.json"

echo ""
echo "🎯 All examples completed!"