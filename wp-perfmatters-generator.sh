#!/bin/bash

set -e

API_URL="https://perfmatters.checkmysite.app"
WP_FLAGS="--allow-root --skip-plugins --skip-themes --quiet"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

check_requirements() {
    command -v wp >/dev/null || error "WP-CLI not found"
    wp core is-installed $WP_FLAGS 2>/dev/null || error "WordPress not found"
    curl -sf "$API_URL/health" >/dev/null || error "API unreachable"
}

check_api() {
    if ! curl -sf "$API_URL/health" >/dev/null 2>&1; then
        print_error "API is not reachable at $API_URL"
        exit 1
    fi
    print_success "API connection verified"
}

get_wp_data() {
    local site_url=$(wp option get siteurl --allow-root --skip-plugins --skip-themes --quiet 2>/dev/null || echo "")
    local plugins=$(wp plugin list --status=active --field=name --format=json --allow-root --skip-plugins --skip-themes --quiet 2>/dev/null || echo "[]")
    local theme=$(wp theme list --status=active --field=name --format=csv --allow-root --skip-plugins --skip-themes --quiet 2>/dev/null | head -1)
    local parent=$(wp theme get "$theme" --field=parent --allow-root --skip-plugins --skip-themes --quiet 2>/dev/null || echo "false")
    
    [ "$parent" != "false" ] && theme="$parent"
    
    echo "$site_url" "$plugins" "$theme"
}

generate_config() {
    read site_url plugins theme <<< "$1"
    
    local payload="{\"plugins\":$plugins,\"theme\":\"$theme\",\"domain\":\"$site_url\",\"analyze_domain\":true}"
    local filename="perfmatters-config-$(date +%Y%m%d-%H%M%S).json"
    
    print_status "Generating configuration..."
    
    if curl -sf -X POST "$API_URL/generate-config" \
        -H "Content-Type: application/json" \
        -d "$payload" \
        -o "$filename"; then
        print_success "Configuration saved: $filename"
    else
        print_error "Failed to generate configuration"
        exit 1
    fi
}

main() {
    echo -e "${BLUE}WordPress Perfmatters Config Generator${NC}"
    echo "======================================"
    
    if ! command -v wp >/dev/null || ! wp core is-installed --allow-root --skip-plugins --skip-themes --quiet 2>/dev/null; then
        print_error "WP-CLI not found or not in WordPress directory"
        exit 1
    fi
    
    check_api
    
    local wp_data=$(get_wp_data)
    local site_url=$(echo "$wp_data" | cut -d' ' -f1)
    local plugins_count=$(echo "$wp_data" | cut -d' ' -f2 | jq length 2>/dev/null || echo "0")
    local theme=$(echo "$wp_data" | cut -d' ' -f3)
    
    print_status "Site: $site_url"
    print_status "Plugins: $plugins_count active"
    print_status "Theme: $theme"
    print_status "Domain analysis: enabled"
    
    echo
    read -p "Generate Perfmatters config? (y/N): " -n 1 -r
    echo
    
    [[ $REPLY =~ ^[Yy]$ ]] && generate_config "$wp_data"
}

main "$@"