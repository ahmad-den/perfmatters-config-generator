#!/bin/bash

set -e

API_URL="https://perfmatters.checkmysite.app"
SITE_URL=""
ANALYZE_DOMAIN=true

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -u, --api-url URL       Custom API URL (default: https://perfmatters.checkmysite.app)"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Note: Domain analysis is always enabled for ad detection"
    echo ""
    echo "Examples:"
    echo "  $0                      Generate config with ad detection"
    echo "  $0 -u http://localhost:8080  Use local API"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--api-url)
            API_URL="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

check_wp_cli() {
    if ! command -v wp &> /dev/null; then
        print_error "WP-CLI is not installed or not in PATH"
        print_error "Please install WP-CLI: https://wp-cli.org/"
        exit 1
    fi
    
    if ! wp core is-installed --allow-root --skip-plugins --skip-themes --quiet 2>/dev/null; then
        print_error "Not in a WordPress directory or WordPress not installed"
        print_error "Please run this script from your WordPress root directory"
        exit 1
    fi
    
    print_success "WP-CLI found and WordPress detected"
}

get_site_url() {
    SITE_URL=$(wp option get siteurl --allow-root --skip-plugins --skip-themes 2>/dev/null || wp option get home --allow-root --skip-plugins --skip-themes 2>/dev/null || echo "")
    if [ -n "$SITE_URL" ]; then
        print_status "Site URL: $SITE_URL"
    else
        print_warning "Could not detect site URL"
    fi
}

get_active_plugins() {
    print_status "Fetching active plugins..."
    
    local plugins_raw=$(wp plugin list --status=active --field=name --format=csv --allow-root --skip-plugins --skip-themes 2>/dev/null || echo "")
    
    if [ -z "$plugins_raw" ]; then
        print_warning "No active plugins found"
        echo "[]"
        return
    fi
    
    local plugins_json="["
    local first=true
    
    while IFS= read -r plugin; do
        if [ -n "$plugin" ]; then
            if [ "$first" = true ]; then
                plugins_json="$plugins_json\"$plugin\""
                first=false
            else
                plugins_json="$plugins_json,\"$plugin\""
            fi
            print_success "  → $plugin"
        fi
    done <<< "$plugins_raw"
    
    plugins_json="$plugins_json]"
    
    local plugin_count=$(echo "$plugins_raw" | grep -c . || echo "0")
    print_success "Found $plugin_count active plugins"
    echo "$plugins_json"
}

get_themes() {
    print_status "Fetching active theme..."
    
    local active_theme=$(wp theme list --status=active --field=name --format=csv --allow-root --skip-plugins --skip-themes 2>/dev/null | head -1)
    
    if [ -z "$active_theme" ]; then
        print_warning "No active theme found"
        echo ""
        return
    fi
    
    print_success "Active theme: $active_theme"
    
    local parent_theme=$(wp theme get "$active_theme" --field=parent --allow-root --skip-plugins --skip-themes 2>/dev/null || echo "")
    
    if [ -n "$parent_theme" ] && [ "$parent_theme" != "false" ]; then
        print_success "Parent theme detected: $parent_theme"
        echo "$parent_theme"
    else
        echo "$active_theme"
    fi
}

call_api() {
    local plugins_json="$1"
    local theme="$2"
    
    print_status "Calling Perfmatters API..."
    print_status "API URL: $API_URL"
    
    local json_payload="{\"plugins\": $plugins_json, \"theme\": \"$theme\""
    
    if [ "$ANALYZE_DOMAIN" = true ] && [ -n "$SITE_URL" ]; then
        json_payload="$json_payload, \"domain\": \"$SITE_URL\", \"analyze_domain\": true"
        print_status "Domain analysis enabled for: $SITE_URL"
    fi
    
    json_payload="$json_payload}"
    
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local filename="perfmatters-config-$timestamp.json"
    
    print_status "Sending request to API..."
    
    local response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/generate-config" \
        -H "Content-Type: application/json" \
        -d "$json_payload" \
        --output "$filename" 2>/dev/null || echo -e "\n000")
    
    local http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ]; then
        print_success "Configuration generated successfully!"
        print_success "File saved as: $filename"
        
        local file_size=$(ls -lh "$filename" | awk '{print $5}')
        print_status "File size: $file_size"
        
        echo ""
        print_status "Next steps:"
        echo "1. Go to your WordPress admin → Perfmatters → Tools"
        echo "2. Click 'Import Settings'"
        echo "3. Upload the file: $filename"
        echo "4. Click 'Import Settings' to apply the configuration"
        
    else
        print_error "API call failed with HTTP code: $http_code"
        
        if [ -f "$filename" ]; then
            local error_msg=$(cat "$filename" 2>/dev/null | grep -o '"error":"[^"]*"' | cut -d'"' -f4 2>/dev/null || echo "")
            if [ -n "$error_msg" ]; then
                print_error "Error message: $error_msg"
            fi
            rm -f "$filename"
        fi
        exit 1
    fi
}

test_api() {
    print_status "Testing API connectivity..."
    
    local health_response=$(curl -s -w "\n%{http_code}" "$API_URL/health" 2>/dev/null || echo -e "\n000")
    local http_code=$(echo "$health_response" | tail -n1)
    
    if [ "$http_code" = "200" ]; then
        print_success "API is accessible"
        return 0
    else
        print_error "Cannot reach API at $API_URL"
        print_error "HTTP code: $http_code"
        return 1
    fi
}

main() {
    echo "🚀 WordPress Perfmatters Configuration Generator"
    echo "================================================"
    echo ""
    
    check_wp_cli
    
    if ! test_api; then
        exit 1
    fi
    
    get_site_url
    
    local plugins_json=$(get_active_plugins)
    local theme=$(get_themes)
    
    echo ""
    print_status "Summary:"
    echo "  Plugins: $(echo "$plugins_json" | grep -o ',' | wc -l | awk '{print $1+1}') found"
    echo "  Theme: $theme"
    echo "  Domain analysis: enabled (always)"
    echo ""
    
    read -p "Generate Perfmatters configuration? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Operation cancelled"
        exit 0
    fi
    
    call_api "$plugins_json" "$theme"
}

main "$@"