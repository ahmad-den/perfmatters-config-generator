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

get_wp_data() {
    local site_url=$(wp option get siteurl $WP_FLAGS 2>/dev/null || wp option get home $WP_FLAGS 2>/dev/null)
    local plugins=$(wp plugin list --status=active --field=name --format=json $WP_FLAGS 2>/dev/null || echo "[]")
    local theme=$(wp theme list --status=active --field=name --format=csv $WP_FLAGS 2>/dev/null | head -1)
    local parent=$(wp theme get "$theme" --field=parent $WP_FLAGS 2>/dev/null || echo "false")
    
    [ "$parent" != "false" ] && theme="$parent"
    
    echo "$site_url|$plugins|$theme"
}

generate_config() {
    local data="$1"
    local site_url=$(echo "$data" | cut -d'|' -f1)
    local plugins=$(echo "$data" | cut -d'|' -f2)
    local theme=$(echo "$data" | cut -d'|' -f3)
    
    local payload="{\"plugins\":$plugins,\"theme\":\"$theme\",\"domain\":\"$site_url\",\"analyze_domain\":true}"
    local filename="perfmatters-config-$(date +%Y%m%d-%H%M%S).json"
    
    local response=$(curl -s -w "%{http_code}" -X POST "$API_URL/generate-config" \
        -H "Content-Type: application/json" \
        -d "$payload" \
        -o "$filename")
    
    [ "$response" = "200" ] || error "API failed with code $response"
    success "Config saved: $filename"
}

main() {
    log "WordPress Perfmatters Config Generator"
    
    check_requirements
    success "Requirements check passed"
    
    log "Fetching WordPress data..."
    local wp_data=$(get_wp_data)
    local site_url=$(echo "$wp_data" | cut -d'|' -f1)
    local plugins_count=$(echo "$wp_data" | cut -d'|' -f2 | jq length 2>/dev/null || echo "0")
    local theme=$(echo "$wp_data" | cut -d'|' -f3)
    
    log "Site: $site_url"
    log "Plugins: $plugins_count active"
    log "Theme: $theme"
    
    read -p "Generate config? (y/N): " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] || exit 0
    
    generate_config "$wp_data"
}

main "$@"