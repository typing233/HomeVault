const { createApp } = Vue;

createApp({
    data() {
        return {
            currentView: 'dashboard',
            dashboard: { total_items: 0, total_rooms: 0, total_categories: 0, expiring_soon: [], expired: [] },
            rooms: [],
            categories: [],
            items: [],
            currentItem: null,
            filter: { search: '', room_id: '', category_id: '' },
            searchTimeout: null,
            roomForm: { id: null, name: '', description: '' },
            categoryForm: { id: null, name: '', description: '' },
            itemForm: { id: null, name: '', description: '', room_id: null, purchase_date: '', price: null, warranty_expires: '', warranty_notes: '', category_ids: [] },
            toast: { show: false, message: '', type: 'success' },
            roomModal: null,
            categoryModal: null
        };
    },
    mounted() {
        this.roomModal = new bootstrap.Modal(document.getElementById('roomModal'));
        this.categoryModal = new bootstrap.Modal(document.getElementById('categoryModal'));
        this.loadDashboard();
        this.loadRooms();
        this.loadCategories();
    },
    methods: {
        async api(url, options = {}) {
            const res = await fetch(url, {
                headers: { 'Content-Type': 'application/json', ...options.headers },
                ...options
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({ error: '请求失败' }));
                throw new Error(err.error || '请求失败');
            }
            if (res.status === 204) return null;
            return res.json();
        },

        showToast(message, type = 'success') {
            this.toast = { show: true, message, type };
            setTimeout(() => { this.toast.show = false; }, 3000);
        },

        navigate(view) {
            this.currentView = view;
            if (view === 'dashboard') this.loadDashboard();
            if (view === 'items') this.loadItems();
            if (view === 'rooms') this.loadRooms();
            if (view === 'categories') this.loadCategories();
        },

        // Dashboard
        async loadDashboard() {
            try {
                this.dashboard = await this.api('/api/dashboard');
            } catch (e) { this.showToast(e.message, 'error'); }
        },

        // Rooms
        async loadRooms() {
            try { this.rooms = await this.api('/api/rooms'); }
            catch (e) { this.showToast(e.message, 'error'); }
        },

        openRoomModal(room = null) {
            if (room) {
                this.roomForm = { id: room.id, name: room.name, description: room.description };
            } else {
                this.roomForm = { id: null, name: '', description: '' };
            }
            this.roomModal.show();
        },

        async saveRoom() {
            try {
                if (this.roomForm.id) {
                    await this.api(`/api/rooms/${this.roomForm.id}`, { method: 'PUT', body: JSON.stringify(this.roomForm) });
                    this.showToast('房间更新成功');
                } else {
                    await this.api('/api/rooms', { method: 'POST', body: JSON.stringify(this.roomForm) });
                    this.showToast('房间创建成功');
                }
                this.roomModal.hide();
                this.loadRooms();
            } catch (e) { this.showToast(e.message, 'error'); }
        },

        async deleteRoom(room) {
            if (!confirm(`确定删除房间"${room.name}"吗？该房间下的物品不会被删除，但会取消关联。`)) return;
            try {
                await this.api(`/api/rooms/${room.id}`, { method: 'DELETE' });
                this.showToast('房间删除成功');
                this.loadRooms();
            } catch (e) { this.showToast(e.message, 'error'); }
        },

        // Categories
        async loadCategories() {
            try { this.categories = await this.api('/api/categories'); }
            catch (e) { this.showToast(e.message, 'error'); }
        },

        openCategoryModal(cat = null) {
            if (cat) {
                this.categoryForm = { id: cat.id, name: cat.name, description: cat.description };
            } else {
                this.categoryForm = { id: null, name: '', description: '' };
            }
            this.categoryModal.show();
        },

        async saveCategory() {
            try {
                if (this.categoryForm.id) {
                    await this.api(`/api/categories/${this.categoryForm.id}`, { method: 'PUT', body: JSON.stringify(this.categoryForm) });
                    this.showToast('分类更新成功');
                } else {
                    await this.api('/api/categories', { method: 'POST', body: JSON.stringify(this.categoryForm) });
                    this.showToast('分类创建成功');
                }
                this.categoryModal.hide();
                this.loadCategories();
            } catch (e) { this.showToast(e.message, 'error'); }
        },

        async deleteCategory(cat) {
            if (!confirm(`确定删除分类"${cat.name}"吗？`)) return;
            try {
                await this.api(`/api/categories/${cat.id}`, { method: 'DELETE' });
                this.showToast('分类删除成功');
                this.loadCategories();
            } catch (e) { this.showToast(e.message, 'error'); }
        },

        // Items
        async loadItems() {
            try {
                const params = new URLSearchParams();
                if (this.filter.search) params.set('search', this.filter.search);
                if (this.filter.room_id) params.set('room_id', this.filter.room_id);
                if (this.filter.category_id) params.set('category_id', this.filter.category_id);
                this.items = await this.api(`/api/items?${params.toString()}`);
            } catch (e) { this.showToast(e.message, 'error'); }
        },

        debounceSearch() {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => this.loadItems(), 300);
        },

        resetFilter() {
            this.filter = { search: '', room_id: '', category_id: '' };
            this.loadItems();
        },

        openItemForm(item = null) {
            if (item) {
                this.itemForm = {
                    id: item.id,
                    name: item.name,
                    description: item.description,
                    room_id: item.room_id,
                    purchase_date: item.purchase_date || '',
                    price: item.price,
                    warranty_expires: item.warranty_expires || '',
                    warranty_notes: item.warranty_notes || '',
                    category_ids: item.categories.map(c => c.id)
                };
            } else {
                this.itemForm = { id: null, name: '', description: '', room_id: null, purchase_date: '', price: null, warranty_expires: '', warranty_notes: '', category_ids: [] };
            }
            this.currentView = 'item-form';
        },

        async saveItem() {
            try {
                const payload = { ...this.itemForm };
                if (!payload.price) payload.price = null;
                if (!payload.room_id) payload.room_id = null;

                if (payload.id) {
                    await this.api(`/api/items/${payload.id}`, { method: 'PUT', body: JSON.stringify(payload) });
                    this.showToast('物品更新成功');
                } else {
                    await this.api('/api/items', { method: 'POST', body: JSON.stringify(payload) });
                    this.showToast('物品创建成功');
                }
                this.navigate('items');
            } catch (e) { this.showToast(e.message, 'error'); }
        },

        async deleteItem(item) {
            if (!confirm(`确定删除物品"${item.name}"吗？相关附件也会被删除。`)) return;
            try {
                await this.api(`/api/items/${item.id}`, { method: 'DELETE' });
                this.showToast('物品删除成功');
                this.loadItems();
            } catch (e) { this.showToast(e.message, 'error'); }
        },

        async viewItem(id) {
            try {
                this.currentItem = await this.api(`/api/items/${id}`);
                this.currentView = 'item-detail';
            } catch (e) { this.showToast(e.message, 'error'); }
        },

        // Attachments
        async uploadAttachment(event) {
            const files = event.target.files;
            if (!files.length) return;

            for (const file of files) {
                const formData = new FormData();
                formData.append('file', file);
                try {
                    await fetch(`/api/items/${this.currentItem.id}/attachments`, { method: 'POST', body: formData });
                } catch (e) {
                    this.showToast(`上传${file.name}失败`, 'error');
                }
            }
            this.showToast('附件上传成功');
            this.currentItem = await this.api(`/api/items/${this.currentItem.id}`);
            event.target.value = '';
        },

        async deleteAttachment(att) {
            if (!confirm(`确定删除附件"${att.original_filename}"吗？`)) return;
            try {
                await this.api(`/api/attachments/${att.id}`, { method: 'DELETE' });
                this.showToast('附件删除成功');
                this.currentItem = await this.api(`/api/items/${this.currentItem.id}`);
            } catch (e) { this.showToast(e.message, 'error'); }
        },

        // CSV export
        exportCSV() {
            const params = new URLSearchParams();
            if (this.filter.search) params.set('search', this.filter.search);
            if (this.filter.room_id) params.set('room_id', this.filter.room_id);
            if (this.filter.category_id) params.set('category_id', this.filter.category_id);
            window.location.href = `/api/items/export?${params.toString()}`;
        },

        // Warranty helpers
        warrantyRowClass(item) {
            if (item.warranty_status === 'expired') return 'table-danger-light';
            if (item.warranty_status === 'expiring_soon') return 'table-warning-light';
            return '';
        },

        warrantyBadgeClass(item) {
            if (item.warranty_status === 'expired') return 'bg-danger';
            if (item.warranty_status === 'expiring_soon') return 'bg-warning text-dark';
            if (item.warranty_status === 'active') return 'bg-success';
            return 'bg-secondary';
        },

        warrantyText(item) {
            if (item.warranty_status === 'expired') return '已过保';
            if (item.warranty_status === 'expiring_soon') return '即将过保';
            if (item.warranty_status === 'active') return '保修中';
            return '未设置';
        },

        // File helpers
        isImage(type) {
            return type && type.startsWith('image/');
        },

        isPreviewable(type) {
            return type && (type.startsWith('image/') || type === 'application/pdf');
        },

        fileIcon(type) {
            if (!type) return 'bi-file-earmark';
            if (type.startsWith('image/')) return 'bi-file-earmark-image text-success';
            if (type === 'application/pdf') return 'bi-file-earmark-pdf text-danger';
            if (type.includes('word') || type.includes('document')) return 'bi-file-earmark-word text-primary';
            if (type.includes('sheet') || type.includes('excel')) return 'bi-file-earmark-excel text-success';
            return 'bi-file-earmark text-secondary';
        },

        formatFileSize(bytes) {
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
            return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        }
    }
}).mount('#app');
