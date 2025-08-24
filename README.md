# Perfmatters Configuration Generator API

A production-ready Python Flask API that automatically generates Perfmatters WordPress plugin configurations based on active plugins and themes.

## Features

### Core Functionality
- Receives WordPress plugin and theme data via POST request
- Uses reference dictionary to map plugins/themes to optimization settings
- Generates pre-populated Perfmatters JSON configuration
- Populates three key fields: `js_exclusions`, `delay_js_exclusions`, and `rucss_excluded_stylesheets`
- Applies universal exclusions for analytics, ads, social media scripts, and core WordPress files

## Quick Start

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Start the API:**
```bash
python app.py
```

3. **Test the API:**
```bash
python test_api.py
```

The API will run on `http://localhost:5000` by default.

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd perfmatters-config-api
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create environment file:
```bash
cp .env.example .env
```

5. Create necessary directories:
```bash
mkdir -p logs templates config
```

## Configuration

### Environment Variables
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 5000)
- `DEBUG`: Debug mode (default: False)
- `WORKERS`: Number of Gunicorn workers (default: 4)

### Configuration Files
- `templates/default_template.json`: Base Perfmatters configuration template
- `config/optimization_dictionary.json`: Plugin/theme optimization mappings

## API Endpoints

### POST /generate-config
Main endpoint to generate Perfmatters configuration.

**Request Body:**
```json
{
  "plugins": ["woocommerce", "elementor", "contact-form-7"],
  "theme": "astra"
}
```

**Response:**
```json
{
  "success": true,
  "config": {
    "perfmatters_options": { ... },
    "perfmatters_tools": { ... }
  },
  "processing_info": {
    "plugins_processed": 3,
    "theme_processed": true
  },
  "generated_at": "2024-01-15T10:30:00"
}
```

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00",
  "version": "1.0.0"
}
```

### POST /reload-config
Reload configuration files without restarting server.

**Response:**
```json
{
  "success": true,
  "message": "Configuration files reloaded successfully",
  "timestamp": "2024-01-15T10:30:00"
}
```

## Usage Examples

### 1. Basic Configuration Generation
```bash
curl -X POST http://localhost:5000/generate-config \
  -H "Content-Type: application/json" \
  -d '{
    "plugins": ["woocommerce", "elementor", "contact-form-7"],
    "theme": "astra"
  }'
```

### 2. Using with WordPress CLI

**Step 1: Get your WordPress data**
```bash
# Get active plugins
wp plugin list --status=active --field=name

# Get active theme
wp theme list --status=active --field=name
```

**Step 2: Use the data with the API**
```bash
# Example with real WordPress data
curl -X POST http://localhost:5000/generate-config \
  -H "Content-Type: application/json" \
  -d '{
    "plugins": ["woocommerce", "yoast-seo", "elementor", "contact-form-7"],
    "theme": "astra"
  }'
```

### 3. Using with Python
```python
import requests
import json

# Your WordPress data
data = {
    "plugins": ["woocommerce", "elementor", "contact-form-7"],
    "theme": "astra"
}

# Make API request
response = requests.post(
    'http://localhost:5000/generate-config',
    json=data,
    headers={'Content-Type': 'application/json'}
)

if response.status_code == 200:
    config = response.json()
    print("Configuration generated successfully!")
    
    # Save to file for Perfmatters import
    with open('perfmatters_config.json', 'w') as f:
        json.dump(config['config'], f, indent=2)
else:
    print(f"Error: {response.status_code}")
    print(response.text)
```

### 4. Using with JavaScript/Node.js
```javascript
const fetch = require('node-fetch');
const fs = require('fs');

async function generateConfig() {
    const data = {
        plugins: ['woocommerce', 'elementor', 'contact-form-7'],
        theme: 'astra'
    };
    
    try {
        const response = await fetch('http://localhost:5000/generate-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Save configuration for Perfmatters import
            fs.writeFileSync('perfmatters_config.json', JSON.stringify(result.config, null, 2));
            console.log('Configuration generated and saved!');
        } else {
            console.error('Error:', result.error);
        }
    } catch (error) {
        console.error('Request failed:', error);
    }
}

generateConfig();
```

## What Gets Populated

The API focuses on three key Perfmatters fields:

1. **`js_exclusions`** - JavaScript files to exclude from minification/optimization
2. **`delay_js_exclusions`** - JavaScript files to exclude from delay loading
3. **`rucss_excluded_stylesheets`** - Stylesheets to exclude from Remove Unused CSS

### Universal Exclusions (Applied to All Sites)
- Analytics scripts (Google Analytics, Facebook Pixel)
- Core WordPress scripts (jQuery, wp-polyfill)
- Admin and accessibility stylesheets

### Plugin-Specific Exclusions
- **WooCommerce**: Cart fragments, checkout scripts, WooCommerce styles
- **Elementor**: Frontend scripts and styles
- **Contact Form 7**: Form validation scripts and styles

### Theme-Specific Exclusions
- **Astra**: Theme-specific scripts and styles
- **GeneratePress**: GP-specific exclusions
- **Divi**: Divi builder scripts and styles

## Response Format

```json
{
  "success": true,
  "config": {
    "perfmatters_options": {
      "assets": {
        "js_exclusions": "gtag\nanalytics\nwoocommerce\nwc-cart-fragments",
        "delay_js_exclusions": "jquery\njquery-migrate\nwc-checkout\nselect2",
        "rucss_excluded_stylesheets": "admin-bar\ncustomize\nwoocommerce-layout"
      }
    }
  },
  "processing_info": {
    "plugins_processed": 3,
    "theme_processed": true
  },
  "generated_at": "2024-01-15T10:30:00"
}
```

## How to Import into Perfmatters

1. **Generate the configuration** using the API
2. **Copy the `config` object** from the API response
3. **In WordPress admin**, go to Perfmatters → Tools
4. **Click "Import Settings"**
5. **Paste the configuration JSON** and click Import

## Adding New Plugins/Themes

Edit `config/optimization_dictionary.json`:

```json
{
  "plugins": {
    "your-plugin-name": {
      "js_exclusions": ["plugin-script-1", "plugin-script-2"],
      "delay_js_exclusions": ["plugin-delay-script"],
      "rucss_excluded_stylesheets": ["plugin-style"]
    }
  },
  "themes": {
    "your-theme-name": {
      "js_exclusions": [],
      "delay_js_exclusions": ["theme-script"],
      "rucss_excluded_stylesheets": ["theme-style"]
    }
  }
}
```

Then reload the configuration:
```bash
curl -X POST http://localhost:5000/reload-config
```

# Use the data to generate config
curl -X POST http://localhost:5000/generate-config \
  -H "Content-Type: application/json" \
  -d "$(jq -n --argjson plugins "$(jq '[.[] | .name]' plugins.json)" --arg theme "$(jq -r '.[0].name' theme.json)" '{plugins: $plugins, theme: $theme}')"
```

## Development

### Running in Development Mode
```bash
export FLASK_ENV=development
export DEBUG=True
python app.py
```

### Running with Gunicorn (Production)
```bash
gunicorn -c gunicorn.conf.py app:app
```

## Supported Plugins

The API includes optimization mappings for popular WordPress plugins:

- **E-commerce**: WooCommerce, Easy Digital Downloads, MemberPress
- **Page Builders**: Elementor, Divi, Avada
- **Forms**: Contact Form 7, WPForms, Gravity Forms, Ninja Forms
- **SEO**: Yoast SEO, Rank Math
- **Performance**: WP Rocket, W3 Total Cache, WP Super Cache
- **Security**: Wordfence, Akismet
- **Sliders**: Slider Revolution, LayerSlider
- **Learning**: LearnDash, LifterLMS
- **Community**: bbPress, BuddyPress
- **Marketing**: Mailchimp, Jetpack

## Supported Themes

Optimization mappings for popular WordPress themes:

- **Default Themes**: Twenty Twenty-Three, Twenty Twenty-Two, Twenty Twenty-One
- **Popular Themes**: Astra, GeneratePress, OceanWP, Kadence
- **Premium Themes**: Avada, Divi, Enfold

## Error Handling

The API includes comprehensive error handling:

- JSON validation for request data
- Network timeout handling for domain analysis
- Graceful handling of missing configuration files
- Proper HTTP status codes for different error types
- Detailed logging for debugging

## Performance Considerations

- Efficient file loading and caching
- Reasonable timeouts for domain analysis (10 seconds)
- Font preloading limited to top 3 fonts
- Critical images count capped at 10
- Proper user agent headers for website scanning

## Security

- Input validation for all endpoints
- Timeout protection for external requests
- No sensitive data exposure in error messages
- Proper CORS handling for cross-origin requests

## Logging

The API logs important events to help with monitoring:

- Configuration loading status
- Plugin/theme processing results
- Domain analysis results
- Error conditions with stack traces

Log files are stored in the `logs/` directory:
- `access.log`: HTTP access logs
- `error.log`: Application error logs
- `gunicorn.pid`: Process ID file

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add your changes with tests
4. Submit a pull request

## License

This project is licensed under the MIT License.