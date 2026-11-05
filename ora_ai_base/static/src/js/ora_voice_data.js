/** @odoo-module **/
import { Component, proxy, onMounted, onWillUnmount, signal, t, useProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

// Handles real-time data updates and futuristic glassmorphic UI for voice assistant.
export class VoiceData extends Component {
    static template = "ora_ai_base.voice_data";
    props = useProps({
        isTestMode: t.any().optional(false),
        configInfo: t.any().optional({}),
        assistantName: t.any().optional("Assistant"),
        onToggleCall: t.any().optional(() => {}),
    });
    waveCanvasRef = signal && typeof signal.ref === 'function' ? signal.ref() : null;

    setup() {
        this.orm = useService("orm");
        this.phase = 0;
        this.currentAmp = 12;
        this.animId = null;

        this.state = proxy({
            customer: "",
            selectedPartnerId: "",
            products: [],
            conversation: [],
            callState: "idle", // 'idle' | 'connecting' | 'active' | 'ended' | 'error'
            statusMsg: "Click microphone to start",
            activeTranscript: "",
            activeRole: "",
            volume: 0,
            isSpeaking: false,
        });

        // 1. Listen to real-time client events from VAPI SDK
        const onVapiMessage = (ev) => {
            this.handlePayload(ev.detail);
        };
        const onVapiStatus = (ev) => {
            if (ev.detail) {
                if (ev.detail.callState) this.state.callState = ev.detail.callState;
                if (ev.detail.msg) this.state.statusMsg = ev.detail.msg;
            }
        };
        const onVapiVolume = (ev) => {
            if (ev.detail) {
                this.state.volume = ev.detail.volume || 0;
            }
        };
        const onVapiSpeech = (ev) => {
            if (ev.detail) {
                this.state.isSpeaking = Boolean(ev.detail.isSpeaking);
            }
        };

        window.addEventListener("vapi_message", onVapiMessage);
        window.addEventListener("vapi_status", onVapiStatus);
        window.addEventListener("vapi_volume", onVapiVolume);
        window.addEventListener("vapi_speech", onVapiSpeech);

        onWillUnmount(() => {
            window.removeEventListener("vapi_message", onVapiMessage);
            window.removeEventListener("vapi_status", onVapiStatus);
            window.removeEventListener("vapi_volume", onVapiVolume);
            window.removeEventListener("vapi_speech", onVapiSpeech);
            if (this.animId) {
                cancelAnimationFrame(this.animId);
                this.animId = null;
            }
        });

        // 2. Listen to backend notifications via bus_service
        try {
            this.busService = useService("bus_service");
        } catch {
            this.busService = this.env?.services?.bus_service;
        }
        if (this.busService) {
            this.channel = "vapi_voice_channel";
            this.inbound_call_channel = "inbound_call_channel";
            this.busService.addChannel(this.channel);
            this.busService.addChannel(this.inbound_call_channel);
            this.busService.subscribe("notification", (payload) => {
                if (payload) {
                    this.onMessage(payload);
                }
            });
        }

        // 3. Audio visualizer animation loop
        onMounted(() => {
            const startAnimation = () => {
                this.drawWave();
                this.animId = requestAnimationFrame(startAnimation);
            };
            this.animId = requestAnimationFrame(startAnimation);
        });
    }

    onToggleMic() {
        if (typeof this.props.onToggleCall === 'function') {
            this.props.onToggleCall();
        } else {
            window.dispatchEvent(new CustomEvent("ora_toggle_call"));
        }
    }

    drawWave() {
        const canvas = (this.waveCanvasRef && typeof this.waveCanvasRef === 'function' ? this.waveCanvasRef() : null)
            || (typeof document !== "undefined" && document.querySelector(".ora_sine_canvas"));
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        const width = canvas.clientWidth || 320;
        const height = canvas.clientHeight || 130;
        const dpr = window.devicePixelRatio || 1;

        if (canvas.width !== Math.floor(width * dpr) || canvas.height !== Math.floor(height * dpr)) {
            canvas.width = Math.floor(width * dpr);
            canvas.height = Math.floor(height * dpr);
            ctx.scale(dpr, dpr);
        }

        ctx.clearRect(0, 0, width, height);

        const isSpeaking = this.state.isSpeaking || this.state.volume > 0.04;
        const speed = isSpeaking ? 0.055 : 0.022;
        this.phase += speed;

        let targetAmp = 12;
        if (this.state.callState === 'active') {
            targetAmp = 22 + Math.min(this.state.volume * 85, 48);
            if (isSpeaking) {
                targetAmp = Math.max(targetAmp, 34);
            }
        } else if (this.state.callState === 'connecting') {
            targetAmp = 18;
        }
        this.currentAmp += (targetAmp - this.currentAmp) * 0.12;

        const midY = height / 2;

        const renderSine = (color, shadowColor, shadowBlur, lineWidth, ampFactor, freq, phaseOffset) => {
            ctx.save();
            ctx.beginPath();
            ctx.strokeStyle = color;
            ctx.lineWidth = lineWidth;
            if (shadowBlur > 0) {
                ctx.shadowColor = shadowColor;
                ctx.shadowBlur = shadowBlur;
            }

            const step = 2;
            for (let x = 0; x <= width; x += step) {
                const u = x / width;
                const env = Math.sin(Math.PI * u);
                const env2 = env * env;
                const y = midY + env2 * Math.sin(freq * x + this.phase + phaseOffset) * (this.currentAmp * ampFactor);

                if (x === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            }
            ctx.stroke();
            ctx.restore();
        };

        // Layer 1: Electric Blue wide harmonic
        renderSine("rgba(59, 130, 246, 0.45)", "rgba(59, 130, 246, 0.6)", 10, 2.5, 0.75, 0.016, 0.5);

        // Layer 2: Neon Cyan vibrant wave
        renderSine("rgba(56, 189, 248, 0.9)", "rgba(56, 189, 248, 0.95)", 14, 2.8, 1.0, 0.022, 1.8);

        // Layer 3: Luminous White core wave
        renderSine("rgba(255, 255, 255, 0.95)", "rgba(255, 255, 255, 0.8)", 8, 2.0, 1.25, 0.028, 3.2);
    }

    handlePayload(data) {
        if (!data) return;

        // Conversation array from conversation-update event
        const conv = data.conversation || data.message?.conversation;
        if (Array.isArray(conv) && conv.length > 0) {
            this.state.conversation = conv.filter(m => m.role !== 'system');
        }

        // Live final / partial transcript from Vapi WebRTC
        if (data.type === "transcript" && data.transcript) {
            const role = data.role === "user" ? "user" : "assistant";
            this.state.activeTranscript = data.transcript;
            this.state.activeRole = role;

            if (data.transcriptType === "final") {
                const lastMsg = this.state.conversation[this.state.conversation.length - 1];
                if (!lastMsg || lastMsg.content !== data.transcript || lastMsg.role !== role) {
                    this.state.conversation.push({
                        role: role,
                        content: data.transcript,
                    });
                }
            }
        }

        // Tool calls / Function calls for order details
        const toolCalls = data.toolCalls || data.message?.toolCalls;
        if (Array.isArray(toolCalls)) {
            for (const tc of toolCalls) {
                if (tc?.function?.arguments) {
                    let args = tc.function.arguments;
                    if (typeof args === "string") {
                        try {
                            args = JSON.parse(args);
                        } catch {
                            args = {};
                        }
                    }
                    this.applyOrderDetails(args?.OrderDetails);
                }
            }
        }
        if (data.functionCall) {
            let params = data.functionCall.parameters;
            if (typeof params === "string") {
                try {
                    params = JSON.parse(params);
                } catch {
                    params = {};
                }
            }
            this.applyOrderDetails(params?.OrderDetails);
        }
    }

    applyOrderDetails(orderDetails) {
        if (!orderDetails || this.props?.isTestMode) return;
        const products = orderDetails.Products || orderDetails.products;
        if (Array.isArray(products) && products.length > 0) {
            const prList = products.map(item => ({
                quantity: item.Quantity || item.qty || 1,
                customer: item.Customer || item.customer || "",
                product: item.Product || item.product || "",
                variant: item.Variant || item.variant || "-",
                product_id: item.productId || item.id || ""
            }));
            this.state.products = prList;
            if (prList[0].customer) {
                this.state.customer = prList[0].customer;
            }
        }
    }

    onMessage(notifications) {
        if (!notifications) return;

        // Handle live customer selection from CheckCustomerExists
        if (notifications.value?.type === 'customer_selected') {
            const partnerId = notifications.value.partner_id;
            const partnerName = notifications.value.partner_name;
            if (partnerId) {
                this.state.selectedPartnerId = String(partnerId);
                this.state.customer = partnerName;
            }
            return;
        }

        // If bus notification has a full message with conversation
        if (notifications.value?.message?.conversation) {
            const conversation = notifications.value.message.conversation;
            this.state.conversation = conversation.filter(m => m.role !== 'system');
        } else if (notifications.value) {
            this.handlePayload(notifications.value);
        }

        // If value is a product list array from backend (skip in test mode)
        if (Array.isArray(notifications.value) && !this.props?.isTestMode) {
            const products = notifications.value.map(item => ({
                quantity: item.qty || item.Quantity || 1,
                customer: item.customer || item.Customer || "",
                product: item.product || item.Product || "",
                variant: item.variant || item.Variant || "-",
                product_id: item.id || item.productId || ""
            }));
            if (products.length > 0) {
                this.state.customer = products[0].customer;
                this.state.products = products;
            }
        }
    }
}
