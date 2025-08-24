#!/bin/bash

# WordPress to Perfmatters Configuration Generator
# This script fetches WordPress plugins and themes data and generates Perfmatters config
# Usage: ./wp-perfmatters-config.sh [wordpress-path] [api-url]

set -e

# Configuration
WORDPRESS_PATH="${1:-$(pwd)}"
API_URL="${2:-https://perfmatters.checkmysite.app}"
WP_CLI_ARGS="--allow-root --skip-plugins --skip-themes"
OUTPUT_DIR="perfmatters-configs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if WP-CLI is installed
check_wp_cli() {
    if ! command -v wp &> /dev/null; then
        error "WP-CLI is not installed. Please install WP-CLI first."
        error "Visit: https://wp-cli.org/#installing"
        exit 1
    fi
    
    log "WP-CLI found: $(wp --version)"
}

# Check if we're in a WordPress directory
check_wordpress() {
    cd "$WORDPRESS_PATH" || {
        error "Cannot access WordPress directory: $WORDPRESS_PATH"
        exit 1
    }
    
    if ! wp core is-installed $WP_CLI_ARGS 2>/dev/null; then
        error "WordPress is not installed or not accessible in: $WORDPRESS_PATH"
        error "Make sure you're running this from a WordPress directory or provide the correct path."
        exit 1
    fi
    
    local wp_version=$(wp core version $WP_CLI_ARGS 2>/dev/null)
    local site_url=$(wp option get siteurl $WP_CLI_ARGS 2>/dev/null)
    
    log "WordPress found: v$wp_version"
    log "Site URL: $site_url"
}

# Get active plugins
get_plugins() {
    log "Fetching active plugins..."
    
    local plugins_json=$(wp plugin list --status=active --format=json $WP_CLI_ARGS 2>/dev/null)
    
    if [ -z "$plugins_json" ] || [ "$plugins_json" = "[]" ]; then
        warning "No active plugins found"
        echo "[]"
        return
    fi
    
    # Extract plugin names and convert to array format
    local plugins_array=$(echo "$plugins_json" | jq -r '[.[].name]' 2>/dev/null)
    
    if [ -z "$plugins_array" ]; then
        error "Failed to parse plugins data"
        echo "[]"
        return
    fi
    
    local plugin_count=$(echo "$plugins_array" | jq length)
    log "Found $plugin_count active plugins"
    
    # Show plugin list
    echo "$plugins_json" | jq -r '.[] | "  - \(.name) (v\(.version))"' 2>/dev/null || true
    
    echo "$plugins_array"
}

# Get active theme (including parent theme)
get_themes() {
    log "Fetching active theme..."
    
    # Get active theme
    local active_theme=$(wp theme list --status=active --format=json $WP_CLI_ARGS 2>/dev/null)
    
    if [ -z "$active_theme" ] || [ "$active_theme" = "[]" ]; then
        error "No active theme found"
        echo '""'
        return
    fi
    
    local theme_name=$(echo "$active_theme" | jq -r '.[0].name' 2>/dev/null)
    local theme_version=$(echo "$active_theme" | jq -r '.[0].version' 2>/dev/null)
    local parent_theme=$(echo "$active_theme" | jq -r '.[0].parent // empty' 2>/dev/null)
    
    log "Active theme: $theme_name (v$theme_version)"
    
    # If there's a parent theme, use that instead (child themes often inherit parent optimizations)
    if [ -n "$parent_theme" ] && [ "$parent_theme" != "null" ]; then
        log "Parent theme detected: $parent_theme"
        log "Using parent theme for optimizations: $parent_theme"
        echo "\"$parent_theme\""
    else
        echo "\"$theme_name\""
    fi
}

# Get site domain
get_domain() {
    log "Fetching site domain..."
    
    local site_url=$(wp option get siteurl $WP_CLI_ARGS 2>/dev/null)
    
    if [ -z "$site_url" ]; then
        error "Could not fetch site URL"
        echo '""'
        return
    fi
    
    log "Site domain: $site_url"
    echo "\"$site_url\""
}

# Generate Perfmatters configuration
generate_config() {
    local plugins="$1"
    local theme="$2"
    local domain="$3"
    
    log "Generating Perfmatters configuration..."
    
    # Create output directory
    mkdir -p "$OUTPUT_DIR"
    
    # Prepare JSON payload
    local json_payload=$(jq -n \
        --argjson plugins "$plugins" \
        --argjson theme "$theme" \
        --argjson domain "$domain" \
        '{
            plugins: $plugins,
            theme: $theme,
            domain: $domain,
            analyze_domain: true
        }')
    
    log "API Request payload:"
    echo "$json_payload" | jq .
    
    # Make API request
    local output_file="$OUTPUT_DIR/perfmatters-config-$TIMESTAMP.json"
    
    log "Sending request to API: $API_URL/generate-config"
    
    local response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -H "User-Agent: WordPress-Perfmatters-Generator/1.0" \
        -d "$json_payload" \
        "$API_URL/generate-config")
    
    local http_code=$(echo "$response" | tail -n1)
    local response_body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        # Save the configuration file
        echo "$response_body" > "$output_file"
        
        success "Configuration generated successfully!"
        success "Saved to: $output_file"
        
        # Show summary
        log "Configuration Summary:"
        if command -v jq &> /dev/null; then
            echo "$response_body" | jq -r '
                "  Plugins processed: " + (.processing_info.plugins_processed | tostring) + 
                "\n  Theme processed: " + (.processing_info.theme_processed | tostring) +
                "\n  Generated at: " + .generated_at
            ' 2>/dev/null || echo "  Configuration generated successfully"
        fi
        
        log "Import Instructions:"
        echo "  1. Copy the configuration file to your WordPress admin"
        echo "  2. Go to Perfmatters → Tools → Import Settings"
        echo "  3. Paste the JSON content and click Import"
        
        return 0
    else
        error "API request failed with HTTP code: $http_code"
        error "Response: $response_body"
        
        # Save error response for debugging
        local error_file="$OUTPUT_DIR/error-$TIMESTAMP.json"
        echo "$response_body" > "$error_file"
        warning "Error response saved to: $error_file"
        
        return 1
    fi
}

# Test API connectivity
test_api() {
    log "Testing API connectivity..."
    
    local health_response=$(curl -s -w "\n%{http_code}" "$API_URL/health")
    local http_code=$(echo "$health_response" | tail -n1)
    local response_body=$(echo "$health_response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        success "API is accessible"
        if command -v jq &> /dev/null; then
            echo "$response_body" | jq -r '"  Status: " + .status + "\n  Version: " + .version' 2>/dev/null || true
        fi
        return 0
    else
        error "API is not accessible (HTTP $http_code)"
        error "URL: $API_URL/health"
        error "Response: $response_body"
        return 1
    fi
}

# Show usage information
show_usage() {
    echo "WordPress to Perfmatters Configuration Generator"
    echo ""
    echo "Usage: $0 [wordpress-path] [api-url]"
    echo ""
    echo "Arguments:"
    echo "  wordpress-path    Path to WordPress installation (default: current directory)"
    echo "  api-url          Perfmatters API URL (default: https://perfmatters.checkmysite.app)"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Use current directory and default API"
    echo "  $0 /var/www/html                     # Specify WordPress path"
    echo "  $0 /var/www/html http://localhost:8080  # Custom WordPress path and API URL"
    echo ""
    echo "Requirements:"
    echo "  - WP-CLI installed and accessible"
    echo "  - WordPress installation with active plugins/themes"
    echo "  - Internet connection to reach the API"
    echo "  - jq (optional, for better JSON formatting)"
}

# Main execution
main() {
    echo "🚀 WordPress to Perfmatters Configuration Generator"
    echo "=================================================="
    
    # Show usage if help requested
    if [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
        show_usage
        exit 0
    fi
    
    # Check dependencies
    check_wp_cli
    check_wordpress
    
    # Test API connectivity
    if ! test_api; then
        error "Cannot proceed without API access"
        exit 1
    fi
    
    # Fetch WordPress data
    local plugins=$(get_plugins)
    local theme=$(get_themes)
    local domain=$(get_domain)
    
    echo ""
    log "WordPress Data Summary:"
    echo "  Plugins: $(echo "$plugins" | jq length) active"
    echo "  Theme: $(echo "$theme" | tr -d '"')"
    echo "  Domain: $(echo "$domain" | tr -d '"')"
    echo ""
    
    # Generate configuration
    if generate_config "$plugins" "$theme" "$domain"; then
        echo ""
        success "🎉 Perfmatters configuration generated successfully!"
        echo ""
        echo "Next steps:"
        echo "1. Go to your WordPress admin → Perfmatters → Tools"
        echo "2. Click 'Import Settings'"
        echo "3. Upload or paste the generated JSON configuration"
        echo "4. Review and save the settings"
        echo ""
    else
        error "Failed to generate configuration"
        exit 1
    fi
}

# Run main function
main "$@"