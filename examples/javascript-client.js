/**
 * JavaScript client example for Perfmatters API
 */

class PerfmattersClient {
    constructor(apiUrl = 'https://perfmatters.checkmysite.app') {
        this.apiUrl = apiUrl.replace(/\/$/, '');
    }

    async healthCheck() {
        try {
            const response = await fetch(`${this.apiUrl}/health`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Health check failed:', error);
            return null;
        }
    }

    async generateConfig(plugins, theme, domain = null, analyzeDomain = false) {
        const data = {
            plugins: plugins,
            theme: theme
        };

        if (domain) {
            data.domain = domain;
            data.analyze_domain = analyzeDomain;
        }

        try {
            const response = await fetch(`${this.apiUrl}/generate-config`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            // Return the blob for file download
            return await response.blob();
        } catch (error) {
            console.error('Config generation failed:', error);
            return null;
        }
    }

    // Helper method to download the config file
    downloadConfig(blob, filename = 'perfmatters-config.json') {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    }
}

// Usage Examples
async function examples() {
    const client = new PerfmattersClient();

    // Health check
    console.log('🔍 Checking API health...');
    const health = await client.healthCheck();
    if (health) {
        console.log('✅ API is healthy:', health);
    } else {
        console.log('❌ API health check failed');
        return;
    }

    // Example 1: Basic configuration
    console.log('\n📋 Generating basic configuration...');
    const basicConfig = await client.generateConfig(
        ['woocommerce', 'elementor', 'contact-form-7'],
        'astra'
    );
    
    if (basicConfig) {
        client.downloadConfig(basicConfig, 'perfmatters-basic-config.json');
        console.log('✅ Basic configuration downloaded');
    }

    // Example 2: With domain analysis
    console.log('\n🔍 Generating configuration with domain analysis...');
    const advancedConfig = await client.generateConfig(
        ['woocommerce', 'elementor'],
        'astra',
        'https://example.com',
        true
    );
    
    if (advancedConfig) {
        client.downloadConfig(advancedConfig, 'perfmatters-with-ads-config.json');
        console.log('✅ Advanced configuration downloaded');
    }

    console.log('\n🎯 All examples completed!');
}

// Run examples if in browser
if (typeof window !== 'undefined') {
    // Browser environment
    console.log('Run examples() to test the API');
} else {
    // Node.js environment
    examples();
}