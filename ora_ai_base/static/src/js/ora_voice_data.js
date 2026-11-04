/** @odoo-module **/
import { Component, proxy, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

// Handles real-time data updates for voice assistant interactions.
export class VoiceData extends Component {
    static template = "ora_ai_base.voice_data";

    setup() {
        this.state = proxy({
            customer: "",
            products: [],
            conversation: [],
        });

        // 1. Listen to real-time client events from VAPI SDK
        const onVapiMessage = (ev) => {
            this.handlePayload(ev.detail);
        };
        window.addEventListener("vapi_message", onVapiMessage);
        onWillUnmount(() => {
            window.removeEventListener("vapi_message", onVapiMessage);
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
    }

    handlePayload(data) {
        if (!data) return;

        // Conversation array from conversation-update event
        const conv = data.conversation || data.message?.conversation;
        if (Array.isArray(conv) && conv.length > 0) {
            this.state.conversation = conv.filter(m => m.role !== 'system');
        }

        // Live final transcript from Vapi WebRTC
        if (data.type === "transcript" && data.transcriptType === "final" && data.transcript) {
            const role = data.role === "user" ? "user" : "assistant";
            // Check if last message was the same to prevent duplicates
            const lastMsg = this.state.conversation[this.state.conversation.length - 1];
            if (!lastMsg || lastMsg.content !== data.transcript || lastMsg.role !== role) {
                this.state.conversation.push({
                    role: role,
                    content: data.transcript,
                });
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
        if (!orderDetails || this.props.isTestMode) return;
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

        // If bus notification has a full message with conversation
        if (notifications.value?.message?.conversation) {
            const conversation = notifications.value.message.conversation;
            this.state.conversation = conversation.filter(m => m.role !== 'system');
        } else if (notifications.value) {
            this.handlePayload(notifications.value);
        }

        // If value is a product list array from backend (skip in test mode)
        if (Array.isArray(notifications.value) && !this.props.isTestMode) {
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
