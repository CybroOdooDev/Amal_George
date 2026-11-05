/** @odoo-module **/
import { Component, onMounted, onWillUnmount, proxy, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";
import { useService } from "@web/core/utils/hooks";
import { VoiceData } from "@ora_ai_base/js/ora_voice_data";


class VoiceAssistant extends Component {
    static components = { VoiceData };
    static template = 'ora_ai_base.voice_assistant';
    props = useProps(standardActionServiceProps);

    setup() {
        const action = this.props?.action || {};
        const params = action.params || this.props?.params || {};
        this.assistantId = params.assistant_id || '';
        this.apiKey = params.api_key || '';
        this.isTestMode = Boolean(params.test_mode);
        this.configInfo = {
            provider: params.provider || '',
            model: params.provider_model || '',
            language: params.language || '',
            transcriber: params.transcriber || '',
        };
        this.state = proxy({
            callState: 'idle', // 'idle' | 'connecting' | 'active' | 'ended' | 'error'
            msg: this.isTestMode
                ? `Click microphone to test ${params.assistant_name || 'Assistant'}`
                : `Click microphone to start ${params.assistant_name || 'Assistant'}`,
            assistant_name: params.assistant_name || 'Assistant',
            volume: 0,
            isSpeaking: false,
        });
        try {
            this.userService = useService("user");
        } catch {
            this.userService = this.env?.services?.user;
        }
        this.vapiReady = false;
        this.vapiInstance = null;
        window.assistant = this.assistantId;
        window.apiKey = this.apiKey;

        // Listener for toggle request from child components
        const handleToggleCall = () => this.toggle_call();
        window.addEventListener("ora_toggle_call", handleToggleCall);

        // Clean up Vapi floating button and stop call when leaving this view
        onWillUnmount(() => {
            window.removeEventListener("ora_toggle_call", handleToggleCall);
            if (this.vapiInstance && typeof this.vapiInstance.stop === 'function') {
                try {
                    this.vapiInstance.stop();
                } catch (e) {
                    console.warn("Error stopping VAPI call:", e);
                }
            }
            this.vapiInstance = null;
            window.assistant = null;
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
                    console.error("Failed to load Vapi library.");
                };
                document.head.appendChild(script);
            } else {
                this.vapiReady = true; // already loaded
            }
        });
    }

    toggle_call() {
        if (this.state.callState === 'active' || this.state.callState === 'connecting') {
            this.stop_vapi();
        } else {
            this.start_vapi();
        }
    }

    stop_vapi() {
        if (this.vapiInstance && typeof this.vapiInstance.stop === 'function') {
            try {
                this.vapiInstance.stop();
            } catch (e) {
                console.warn("Error stopping VAPI call:", e);
            }
        }
        this.state.callState = 'ended';
        this.state.msg = "Call ended. Click microphone to start again.";
        this.state.volume = 0;
        this.state.isSpeaking = false;
        window.dispatchEvent(new CustomEvent("vapi_status", {
            detail: { callState: 'ended', msg: this.state.msg }
        }));
        window.dispatchEvent(new CustomEvent("vapi_speech", {
            detail: { isSpeaking: false }
        }));
        window.dispatchEvent(new CustomEvent("vapi_volume", {
            detail: { volume: 0 }
        }));
    }

    async start_vapi() {
        const self = this;

        if (!this.vapiReady || !window.vapiSDK || typeof window.vapiSDK.run !== 'function') {
            self.state.msg = "Voice assistant not ready. Please wait...";
            self.state.callState = 'connecting';
            window.dispatchEvent(new CustomEvent("vapi_status", {
                detail: { callState: 'connecting', msg: self.state.msg }
            }));
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

        self.state.callState = 'connecting';
        self.state.msg = "Connecting to assistant...";
        window.dispatchEvent(new CustomEvent("vapi_status", {
            detail: { callState: 'connecting', msg: self.state.msg }
        }));

        const action = self.props?.action || {};
        const params = action.params || self.props?.params || {};
        const apiKey = params.api_key || self.apiKey || window.apiKey;
        const assistantId = params.assistant_id || self.assistantId || window.assistant;

        const VAPI = await window.vapiSDK.run({
            apiKey: apiKey,
            assistant: assistantId,
        });
        if (!VAPI || typeof VAPI.start !== 'function') {
            self.state.callState = 'error';
            self.state.msg = "Failed to initialize the assistant.";
            window.dispatchEvent(new CustomEvent("vapi_status", {
                detail: { callState: 'error', msg: self.state.msg }
            }));
            console.error("VAPI object is invalid.");
            return;
        }
        self.vapiInstance = VAPI;
        const variableValues = {};
        if (self.isTestMode) {
            variableValues.test_mode = "true";
        }
        const currentUserId = params.user_id ||
            (typeof odoo !== "undefined" && odoo.session_info?.uid) ||
            window.odoo?.session_info?.uid ||
            self.userService?.userId ||
            self.userService?.id ||
            self.env?.services?.user?.userId ||
            self.env?.services?.user?.id ||
            null;
        if (currentUserId) {
            variableValues.salesperson_id = String(currentUserId);
            variableValues.user_id = String(currentUserId);
        }
        const metadata = {};
        if (currentUserId) {
            metadata.salesperson_id = String(currentUserId);
            metadata.user_id = String(currentUserId);
        }
        const assistantOverrides = {
            variableValues,
            ...(Object.keys(metadata).length > 0 ? { metadata } : {}),
        };

        VAPI.start(assistantId, assistantOverrides);

        VAPI.on("call-start", () => {
            self.state.callState = 'active';
            self.state.msg = "Listening... Speak now";
            window.dispatchEvent(new CustomEvent("vapi_status", {
                detail: { callState: 'active', msg: self.state.msg }
            }));
        });

        VAPI.on("call-end", () => {
            self.state.callState = 'ended';
            self.state.msg = "Thank you for using the assistant.";
            self.state.volume = 0;
            self.state.isSpeaking = false;
            window.dispatchEvent(new CustomEvent("vapi_status", {
                detail: { callState: 'ended', msg: self.state.msg }
            }));
            window.dispatchEvent(new CustomEvent("vapi_speech", {
                detail: { isSpeaking: false }
            }));
            window.dispatchEvent(new CustomEvent("vapi_volume", {
                detail: { volume: 0 }
            }));
        });

        VAPI.on("speech-start", () => {
            self.state.isSpeaking = true;
            window.dispatchEvent(new CustomEvent("vapi_speech", {
                detail: { isSpeaking: true }
            }));
        });

        VAPI.on("speech-end", () => {
            self.state.isSpeaking = false;
            window.dispatchEvent(new CustomEvent("vapi_speech", {
                detail: { isSpeaking: false }
            }));
        });

        VAPI.on("volume-level", (volume) => {
            self.state.volume = volume || 0;
            window.dispatchEvent(new CustomEvent("vapi_volume", {
                detail: { volume: volume || 0 }
            }));
        });

        VAPI.on("message", (message) => {
            if (message.type === "transcript") {
                const prefix = message.role === "user" ? "🧑 Me" : "🤖 Assistant";
                if (message.transcriptType === "partial") {
                    self.state.msg = `${prefix}: ${message.transcript}`;
                }
                if (message.transcriptType === "final") {
                    self.state.msg = `${prefix}: ${message.transcript}`;
                }
            }
            window.dispatchEvent(new CustomEvent("vapi_message", { detail: message }));
        });

        VAPI.on("error", async (e) => {
            console.error("VAPI Error:", e);
            let errMsg = "Something went wrong. Please try again.";
            if (e && typeof e === 'object') {
                if (e.message) {
                    errMsg = e.message;
                } else if (e.error?.message) {
                    errMsg = e.error.message;
                } else if (typeof e.json === 'function') {
                    try {
                        const jsonErr = await e.json();
                        if (jsonErr?.message) {
                            errMsg = jsonErr.message;
                        }
                    } catch {}
                }
            }
            self.state.callState = 'error';
            self.state.msg = errMsg;
            window.dispatchEvent(new CustomEvent("vapi_status", {
                detail: { callState: 'error', msg: errMsg }
            }));
        });
    }
}
VoiceAssistant.template = 'ora_ai_base.voice_assistant';
registry.category("actions").add("action_voice_assistant", VoiceAssistant);
