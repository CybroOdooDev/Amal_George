/** @odoo-module **/
import { Component, useState, onWillStart, onWillDestroy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

class KitchenDisplay extends Component {
    static props = { ...standardActionServiceProps };
    static template = "pos_kitchen_display.KitchenDisplay";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
        
        this.state = useState({
            orders: [],
            activeFilter: 'all', // 'all', 'to_cook', 'ready', 'completed'
            currentTime: new Date().toLocaleTimeString(),
            soundEnabled: true,
            isLoaded: false,
        });

        // Clock timer
        this.clockInterval = setInterval(() => {
            this.state.currentTime = new Date().toLocaleTimeString();
            // Update order elapsed times
            this.state.orders.forEach(order => {
                if (order.state !== 'done') {
                    order.elapsedMinutes = Math.floor((new Date() - order.createdTime) / 60000);
                }
            });
        }, 1000);

        onWillStart(async () => {
            await this.loadOrders();
        });

        onWillDestroy(() => {
            clearInterval(this.clockInterval);
            if (this.completionTimeouts) {
                Object.values(this.completionTimeouts).forEach(clearTimeout);
            }
        });
    }

    async loadOrders() {
        try {
            // Fetch active prep/cooking/ready orders
            const activeRecords = await this.orm.searchRead(
                "pos.kitchen.order",
                [["state", "!=", "done"]],
                ["name", "state", "table_name", "shop_name", "create_date"]
            );
            
            // Fetch recent completed orders
            const completedRecords = await this.orm.searchRead(
                "pos.kitchen.order",
                [["state", "=", "done"]],
                ["name", "state", "table_name", "shop_name", "create_date"],
                { order: "id desc", limit: 30 }
            );

            const records = [...activeRecords, ...completedRecords];

            if (records && records.length > 0) {
                const orderIds = records.map(rec => rec.id);
                const lines = await this.orm.searchRead(
                    "pos.kitchen.order.line",
                    [["order_id", "in", orderIds]],
                    ["order_id", "name", "qty", "note", "is_completed"]
                );

                const linesByOrderId = {};
                lines.forEach(line => {
                    const orderId = line.order_id[0];
                    if (!linesByOrderId[orderId]) {
                        linesByOrderId[orderId] = [];
                    }
                    linesByOrderId[orderId].push({
                        id: line.id,
                        name: line.name,
                        qty: line.qty,
                        note: line.note,
                        is_completed: line.is_completed
                    });
                });

                this.state.orders = records.map(rec => {
                    const createdTime = rec.create_date ? new Date(rec.create_date + "Z") : new Date();
                    return {
                        id: rec.id,
                        name: rec.name === '/' ? `Order #${rec.id}` : rec.name,
                        state: rec.state,
                        table: rec.table_name || "Takeaway",
                        shop_name: rec.shop_name || "",
                        createdTime: createdTime,
                        elapsedMinutes: Math.max(0, Math.floor((new Date() - createdTime) / 60000)),
                        items: linesByOrderId[rec.id] || []
                    };
                });
            } else {
                this.state.orders = [];
            }
        } catch (error) {
            console.error("Failed to load orders:", error);
            this.state.orders = [];
        } finally {
            this.state.isLoaded = true;
        }
    }

    getOrderProgress(order) {
        if (!order.items || order.items.length === 0) {
            return 0;
        }
        const completed = order.items.filter(i => i.is_completed).length;
        return Math.round((completed / order.items.length) * 100);
    }

    async toggleItemCompletion(order, item) {
        // If order is completed, don't allow toggling items
        if (order.state === 'done') {
            return;
        }

        item.is_completed = !item.is_completed;
        
        // Write status to the database
        try {
            await this.orm.write("pos.kitchen.order.line", [item.id], {
                is_completed: item.is_completed
            });
        } catch (e) {
            console.error("Failed to update item completion state in DB", e);
        }

        // If the order is in draft, move it to progress
        if (order.state === 'draft') {
            order.state = 'progress';
            try {
                await this.orm.write("pos.kitchen.order", [order.id], { state: 'progress' });
            } catch (e) {
                console.error("Failed to update order state to progress in DB", e);
            }
        }

        // Check if all items in this order are completed
        const allCompleted = order.items.every(i => i.is_completed);
        
        if (allCompleted) {
            // Play sound if enabled
            if (this.state.soundEnabled && typeof Audio !== 'undefined') {
                try {
                    const ctx = new (window.AudioContext || window.webkitAudioContext)();
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();
                    osc.type = "sine";
                    osc.frequency.setValueAtTime(587.33, ctx.currentTime);
                    gain.gain.setValueAtTime(0.05, ctx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.15);
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    osc.start();
                    osc.stop(ctx.currentTime + 0.15);
                } catch (e) {
                    console.log("Audio failed to play", e);
                }
            }

            // progress → ready: update state and reset all checkboxes
            if (order.state === 'progress') {
                order.state = 'ready';
                try {
                    await this.orm.write("pos.kitchen.order", [order.id], { state: 'ready' });
                    this.notification.add(`Order ${order.name} is ready!`, {
                        type: "success",
                    });
                } catch (e) {
                    console.error("Failed to update order state to ready in DB", e);
                }

                // Reset all item checkboxes to unchecked in local state and DB
                const lineIds = order.items.map(i => i.id);
                order.items.forEach(i => { i.is_completed = false; });
                try {
                    await this.orm.write("pos.kitchen.order.line", lineIds, { is_completed: false });
                } catch (e) {
                    console.error("Failed to reset item completion states in DB", e);
                }
            }
            // ready → done (completed) — no button needed, auto-transition
            else if (order.state === 'ready') {
                order.state = 'done';
                try {
                    await this.orm.write("pos.kitchen.order", [order.id], { state: 'done' });
                    this.notification.add(`Order ${order.name} completed!`, {
                        type: "success",
                    });
                } catch (e) {
                    console.error("Failed to update order state to done in DB", e);
                }
            }
        }
    }

    async serveOrder(order) {
        // Play sound if enabled
        if (this.state.soundEnabled && typeof Audio !== 'undefined') {
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = "sine";
                osc.frequency.setValueAtTime(880.00, ctx.currentTime); // A5 note
                gain.gain.setValueAtTime(0.05, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.15);
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start();
                osc.stop(ctx.currentTime + 0.15);
            } catch (e) {
                console.log("Audio failed to play", e);
            }
        }

        try {
            await this.orm.write("pos.kitchen.order", [order.id], { state: 'done' });
            // Instead of deleting it from state completely (which would hide it from 'Completed' filter),
            // we update its local state to 'done' so it transitions filters correctly!
            order.state = 'done';
            this.notification.add(`Order ${order.name} completed and served!`, {
                type: "success",
            });
        } catch (e) {
            console.error("Failed to mark order as done", e);
        }
    }

    setFilter(filter) {
        this.state.activeFilter = filter;
    }

    toggleSound() {
        this.state.soundEnabled = !this.state.soundEnabled;
    }

    get filteredOrders() {
        if (this.state.activeFilter === 'all') {
            return this.state.orders.filter(o => o.state !== 'done');
        }
        if (this.state.activeFilter === 'to_cook') {
            return this.state.orders.filter(o => o.state === 'draft' || o.state === 'progress');
        }
        if (this.state.activeFilter === 'ready') {
            return this.state.orders.filter(o => o.state === 'ready');
        }
        if (this.state.activeFilter === 'completed') {
            return this.state.orders.filter(o => o.state === 'done');
        }
        return this.state.orders;
    }

    get countToCook() {
        return this.state.orders.filter(o => o.state === 'draft' || o.state === 'progress').length;
    }

    get countReady() {
        return this.state.orders.filter(o => o.state === 'ready').length;
    }

    get countCompleted() {
        return this.state.orders.filter(o => o.state === 'done').length;
    }

    get countAll() {
        return this.state.orders.filter(o => o.state !== 'done').length;
    }

    async dismissOrder(order) {
        // Remove from local state immediately so card disappears
        this.state.orders = this.state.orders.filter(o => o.id !== order.id);
        // Permanently delete from the database so it won't come back on refresh
        try {
            await this.orm.unlink("pos.kitchen.order", [order.id]);
        } catch (e) {
            console.error("Failed to delete order from DB", e);
        }
    }

    closeDisplay() {
        window.location.href = '/odoo/point-of-sale';
    }
}

registry.category("actions").add("pos_kitchen_display.kitchen_display", KitchenDisplay);
