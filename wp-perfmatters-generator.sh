# Check if we're in a WordPress directory
if ! wp core is-installed --allow-root --skip-plugins --skip-themes --quiet 2>/dev/null; then
    print_error "Not in a WordPress directory or WordPress not installed"
    print_error "Please run this script from your WordPress root directory"
    exit 1
fi

# Function to get site URL
get_site_url() {
    SITE_URL=$(wp option get siteurl --allow-root --skip-plugins --skip-themes 2>/dev/null || wp option get home --allow-root --skip-plugins --skip-themes 2>/dev/null || echo "")
    if [ -n "$SITE_URL" ]; then
        print_status "Site URL: $SITE_URL"
    else
        print_warning "Could not determine site URL"
    fi
}

# Function to get active plugins
get_active_plugins() {
    print_status "Fetching active plugins..."
    
    # Get active plugins (exclude mu-plugins)
    local plugins_raw=$(wp plugin list --status=active --field=name --format=csv --allow-root --skip-plugins --skip-themes 2>/dev/null || echo "")
    
    if [ -z "$plugins_raw" ]; then
        print_warning "No active plugins found"
        return
    fi
    
    # Convert to array and display
    IFS=',' read -ra PLUGINS <<< "$plugins_raw"
    for plugin in "${PLUGINS[@]}"; do
        print_success "Active plugin: $plugin"
    done
}

# Function to get active theme
get_active_theme() {
    print_status "Fetching active theme..."
    
    # Get active theme
    local active_theme=$(wp theme list --status=active --field=name --format=csv --allow-root --skip-plugins --skip-themes 2>/dev/null | head -1)
    
    if [ -z "$active_theme" ]; then
        print_warning "No active theme found"
        return
    fi
    
    print_success "Active theme: $active_theme"
    
    # Check if it's a child theme and get parent
    local parent_theme=$(wp theme get "$active_theme" --field=parent --allow-root --skip-plugins --skip-themes 2>/dev/null || echo "")
    
    if [ -n "$parent_theme" ] && [ "$parent_theme" != "false" ]; then
        print_success "Parent theme detected: $parent_theme"
    fi
}