// ===== FUNÇÕES GLOBAIS =====

// Máscara para telefone
function mascaraTelefone(input) {
    let value = input.value.replace(/\D/g, '');
    if (value.length <= 10) {
        value = value.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
    } else {
        value = value.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
    }
    input.value = value;
}

// Máscara para CPF
function mascaraCPF(input) {
    let value = input.value.replace(/\D/g, '');
    value = value.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
    input.value = value;
}

// Máscara para data
function mascaraData(input) {
    let value = input.value.replace(/\D/g, '');
    if (value.length > 2 && value.length <= 4) {
        value = value.replace(/(\d{2})(\d{2})/, '$1/$2');
    } else if (value.length > 4) {
        value = value.replace(/(\d{2})(\d{2})(\d{4})/, '$1/$2/$3');
    }
    input.value = value;
}

// Formatação de moeda
function formatarMoeda(valor) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(valor);
}

// Formatação de data
function formatarData(data) {
    const d = new Date(data);
    return d.toLocaleDateString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
}

// Formatação de hora
function formatarHora(hora) {
    const [h, m] = hora.split(':');
    return `${h}:${m}`;
}

// Calcular dias restantes
function diasRestantes(data) {
    const hoje = new Date();
    const prazo = new Date(data);
    const diff = Math.ceil((prazo - hoje) / (1000 * 60 * 60 * 24));
    return diff > 0 ? diff : 0;
}

// Gerar cor aleatória
function corAleatoria() {
    const cores = [
        '#2563eb', '#7c3aed', '#16a34a', '#ea580c',
        '#e11d48', '#0891b2', '#d97706', '#65a30d',
        '#4a7a9c', '#dc2626', '#9333ea', '#059669'
    ];
    return cores[Math.floor(Math.random() * cores.length)];
}

// Debounce para eventos de input
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ===== INICIALIZAÇÃO =====
document.addEventListener('DOMContentLoaded', function() {
    // Aplicar máscaras automáticas
    document.querySelectorAll('[data-mask="telefone"]').forEach(el => {
        el.addEventListener('input', function() {
            mascaraTelefone(this);
        });
    });

    document.querySelectorAll('[data-mask="cpf"]').forEach(el => {
        el.addEventListener('input', function() {
            mascaraCPF(this);
        });
    });

    document.querySelectorAll('[data-mask="data"]').forEach(el => {
        el.addEventListener('input', function() {
            mascaraData(this);
        });
    });

    // Auto-fechar mensagens após 5 segundos
    document.querySelectorAll('.message').forEach(msg => {
        setTimeout(() => {
            msg.style.transition = 'opacity 0.5s ease';
            msg.style.opacity = '0';
            setTimeout(() => msg.remove(), 500);
        }, 5000);
    });
});