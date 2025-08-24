#!/bin/bash

set -e

API_URL="https://perfmatters.checkmysite.app"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_requirements() {
    command -v wp >/dev/null || { print_error "WP-CLI not found"; exit 1; }
    wp core is-installed --quiet 2>/dev/null || { print_error "WordPress not found"; exit 1; }
    curl -sf "$API_URL/health" >/dev/null || { print_error "API unreachable"; exit 1; }
}

get_wp_data() {
    local site_url=$(wp option get siteurl 2>/dev/null || echo "")
    local plugins=$(wp plugin list --status=active --field=name --format=json 2>/dev/null || echo "[]")
    local theme=$(wp theme list --status=active --field=name --format=csv 2>/dev/null | head -1)
    local parent=$(wp theme get "$theme" --field=parent 2>/dev/null || echo "false")
    
    [ "$parent" != "false" ] && theme="$parent"
    
    echo "$site_url" "$plugins" "$theme"
}

generate_config() {
    read -r site_url plugins theme <<< "$1"
    
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

show_help() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -u URL    Set custom API URL"
    echo "  -h        Show this help"
    exit 0
}

main() {
    while getopts "u:h" opt; do
        case $opt in
            u) API_URL="$OPTARG" ;;
            h) show_help ;;
            *) show_help ;;
        esac
    done
    
    echo -e "${BLUE}WordPress Perfmatters Config Generator${NC}"
    echo "======================================"
    
    check_requirements
    
    local wp_data=$(get_wp_data)
    local site_url plugins_count theme
    read -r site_url plugins theme <<< "$wp_data"
    plugins_count=$(echo "$plugins" | jq length 2>/dev/null || echo "0")
    
    print_status "Site: ${site_url:-unknown}"
    print_status "Plugins: $plugins_count active"
    print_status "Theme: ${theme:-unknown}"
    print_status "Domain analysis: enabled (always)"
    
    echo
    read -p "Generate config? (y/N): " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] && generate_config "$wp_data" || echo "Cancelled."
}

main "$@"