/** @odoo-module **/
import { Component, onMounted, onWillUnmount, proxy, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";
import { VoiceData } from "@ora_ai_base/js/ora_voice_data";


class VoiceAssistant extends Component {
    static components = { VoiceData };
    static template = 'ora_ai_base.voice_assistant';
    props = useProps(standardActionServiceProps);

    setup() {
        const action = this.props?.action || {};
        const params = action.params || this.props?.params || {};
        this.isTestMode = Boolean(params.test_mode);
        this.configInfo = {
            provider: params.provider || '',
            model: params.provider_model || '',
            language: params.language || '',
            transcriber: params.transcriber || '',
        };
        this.state = proxy({
            msg: this.isTestMode
                ? `Click here to test ${params.assistant_name || 'Assistant'}`
                : `Click here to start ${params.assistant_name || 'No Assistant'}`,
            assistant_name: params.assistant_name || 'No Assistant',
        });
        this.vapiReady = false;
        this.vapiInstance = null;
        // Store assistant info globally if needed
        window.assistant = params.assistant_id;
        window.apiKey = params.api_key;

        // Clean up Vapi floating button and stop call when leaving this view
        onWillUnmount(() => {
            if (this.vapiInstance && typeof this.vapiInstance.stop === 'function') {
                try {
                    this.vapiInstance.stop();
                } catch (e) {
                    console.warn("Error stopping VAPI call:", e);
                }
            }
            document.querySelectorAll("#vapi-support-btn, .vapi-btn").forEach((el) => {
                try { el.remove(); } catch (e) {}
            });
        });

        // Dynamically load the VAPI SDK
        onMounted(() => {
            document.querySelectorAll("#vapi-support-btn, .vapi-btn").forEach((el) => {
                try { el.remove(); } catch (e) {}
            });
            const existingScript = document.querySelector('script[src="/ora_ai_base/static/src/lib/vapi.min.js"]');
            if (!existingScript) {
                const script = document.createElement("script");
                script.src = "/ora_ai_base/static/src/lib/vapi.min.js";
                script.async = true;
                script.defer = true;
                script.onload = () => {
                    this.vapiReady = true;
                };
                script.onerror = () => {
                    console.error("Go back to the assistant.");
                };
                document.head.appendChild(script);
            } else {
                this.vapiReady = true; // already loaded
            }
        });
    }
    async start_vapi() {
        const self = this;

        if (!this.vapiReady || !window.vapiSDK || typeof window.vapiSDK.run !== 'function') {
            self.state.msg = "🔄 Voice assistant not ready. Please wait...";
            console.warn("VAPI SDK is not ready yet.");
            return;
        }

        // Clean up any previously attached floating button
        document.querySelectorAll("#vapi-support-btn, .vapi-btn").forEach((el) => {
            try { el.remove(); } catch (e) {}
        });
        if (self.vapiInstance && typeof self.vapiInstance.stop === 'function') {
            try {
                self.vapiInstance.stop();
            } catch (e) {
                // ignore
            }
        }

        self.state.msg = "🔊 Starting voice assistant...";
        const action = self.props?.action || {};
        const params = action.params || {};
        const apiKey = params.api_key || window.apiKey;
        const assistantId = params.assistant_id || window.assistant;

        const VAPI = await window.vapiSDK.run({
            apiKey: apiKey,
            assistant: assistantId,
        });
        if (!VAPI || typeof VAPI.start !== 'function') {
            self.state.msg = "❌ Failed to initialize the assistant.";
            console.error("VAPI object is invalid.");
            return;
        }
        self.vapiInstance = VAPI;
        const assistantOverrides = self.isTestMode ? {
            variableValues: {
                test_mode: "true",
            },
        } : undefined;
        if (assistantOverrides) {
            VAPI.start(assistantId, assistantOverrides);
        } else {
            VAPI.start(assistantId);
        }
        VAPI.on("call-end", () => {
            self.state.msg = "✅ Thank you for using the assistant.";
        });
        VAPI.on("message", (message) => {
            if (message.type === "transcript") {
                const prefix = message.role === "user" ? "🧑 Me" : "🤖 Assistant";
                if (message.transcriptType === "partial") {
                    self.state.msg = `${prefix} (typing...): ${message.transcript}`;
                }
                if (message.transcriptType === "final") {
                    self.state.msg = `${prefix}: ${message.transcript}`;
                }
            }
            window.dispatchEvent(new CustomEvent("vapi_message", { detail: message }));
        });
        VAPI.on("error", (e) => {
            console.error("🚨 VAPI Error:", e);
            self.state.msg = "⚠️ Something went wrong. Please try again.";
        });
    }
}
VoiceAssistant.template = 'ora_ai_base.voice_assistant';
registry.category("actions").add("action_voice_assistant", VoiceAssistant);
