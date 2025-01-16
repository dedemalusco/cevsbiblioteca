function toggleAbout() {
    var overlay = document.getElementById('overlay');
    var aboutInfo = document.getElementById('about-info');
    overlay.classList.toggle('hidden');
    aboutInfo.classList.toggle('hidden');
}


function toggleForm(containerId) {
    const container = document.getElementById(containerId);
    container.style.display = container.style.display === 'none' ? 'block' : 'none';
}

function formatarDataHora(data) {
    const date = new Date(data);
    date.setHours(date.getHours());

    // Formatar a data e hora
    const dia = String(date.getDate()).padStart(2, '0');
    const mes = String(date.getMonth() + 1).padStart(2, '0');
    const ano = date.getFullYear();
    const hora = String(date.getHours()).padStart(2, '0');
    const minuto = String(date.getMinutes()).padStart(2, '0');

    return `${dia}/${mes}/${ano} - ${hora}:${minuto}`;
}

// Função para carregar a lista de empréstimos quando a página carregar
window.onload = function () {
    fetch('/livros_emprestados_json')
        .then(response => response.json())
        .then(data => {
            const listaEmprestimos = document.getElementById('lista-emprestimos');
            listaEmprestimos.innerHTML = ''; // Limpar a lista antes de adicionar os novos itens

            data.forEach(emprestimo => {
                const listItem = document.createElement('li');
                listItem.innerHTML = `<strong>${emprestimo.titulo}</strong> - ${emprestimo.autor} - Aluno: ${emprestimo.aluno} - Horário: ${formatarDataHora(emprestimo.horario_emprestimo)} - Quantidade: ${emprestimo.quantidade}`;
                listaEmprestimos.appendChild(listItem);
            });
        })
        .catch(error => console.error('Erro ao carregar a lista de empréstimos:', error));
};
function submitForm(formData, successMessage) {
    fetch('/adicionar_livro', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage('success', successMessage);
            // Atualizar a página automaticamente após 1 segundo se a operação foi bem-sucedida
            setTimeout(function() {
                window.location.reload();
            }, 10);
        } else {
            showMessage('error', 'Erro ao realizar a operação: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        showMessage('error', 'Erro ao realizar a operação: ' + error.message);
    });
}
// Função para enviar o formulário de empréstimo de livro
document.getElementById('form-emprestar-livro').addEventListener('submit', function(event) {
    event.preventDefault(); // Evitar o envio tradicional do formulário
    var formData = new FormData(this); // Coletar os dados do formulário
    fetch('/emprestar_livro', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Mostrar mensagem de sucesso
            showAlert('success', 'Livro emprestado com sucesso.');
            // Atualizar a página após 1 segundo
            setTimeout(function() {
                window.location.reload();
            }, 1000);
        } else {
            // Mostrar mensagem de erro se não tiver sucesso
            showAlert('error', 'Erro ao realizar a operação: ' + data.error);
        }
    })
    .catch(error => {
        // Tratar o erro de comunicação/network
        console.error('Erro:', error);
        showAlert('error', 'Erro ao realizar a operação: ' + error.message);
    });
});

// Função para enviar o formulário de devolução de livro
document.getElementById('form-devolver-livro').addEventListener('submit', function(event) {
    event.preventDefault(); // Evitar o envio tradicional do formulário
    var formData = new FormData(this); // Coletar os dados do formulário
    fetch('/devolver_livro', { // Ajuste a URL conforme a rota correta no seu backend
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            // Novo: Loga o status para diagnóstico
            console.error('Status de Erro:', response.status);
            response.text().then(text => console.error(text)); // Loga a resposta textual para mais detalhes
            throw new Error('A resposta do servidor não foi OK, reveja se o livro, o aluno ou a quantidade está correto.');
        }
        return response.json();
    })
    .then(data => {
        if (data.mensagem) {
            // Mostrar mensagem de sucesso
            showAlert('success', data.mensagem);
            // Atualizar a página após 1 segundo
            setTimeout(function() {
                window.location.reload();
            }, 1000);
        } else {
            // Se a resposta não contiver a chave 'mensagem', assumir que houve um erro
            showAlert('error', 'Erro ao realizar a operação.');
        }
    })
    .catch(error => {
        // Tratar o erro de comunicação/network ou o erro de JSON
        console.error('Erro:', error);
        showAlert('error', 'Erro ao realizar a operação: ' + error.message);
    });
});

// Função para exibir o alerta por um curto período de tempo, com ícone e mensagem
function showAlert(type, message) {
    var alert = document.getElementById('alert');
    var icon = document.createElement('i');
    var iconClass = type === 'success' ? 'fas fa-check-circle' : 'fas fa-times-circle';
    icon.className = iconClass;
    alert.innerHTML = ''; // Limpa o conteúdo existente
    alert.appendChild(icon);
    alert.appendChild(document.createTextNode(message));
    alert.className = type;
    alert.style.display = 'block';
    setTimeout(function() {
        alert.style.display = 'none';
    }, 2000); // 2 segundos
}

function toggleForm(formId) {
    var formContainer = document.getElementById(formId);
    var divContainer = document.querySelector('.divcontainer');
    
    // Se o formulário estiver oculto, exibe-o; caso contrário, oculta-o
    if (formContainer.style.display === 'none') {
        formContainer.style.display = 'block';
        divContainer.style.display = 'block';
    } else {
        formContainer.style.display = 'none';
        // Verifica se todos os formulários estão ocultos e, nesse caso, oculta a div divcontainer
        var allFormsHidden = true;
        var forms = document.querySelectorAll('.form-container');
        forms.forEach(function(form) {
            if (form.style.display !== 'none') {
                allFormsHidden = false;
            }
        });
        if (allFormsHidden) {
            divContainer.style.display = 'none';
        }
    }
}

function toggleList() {
    var listaLivros = document.getElementById('lista-livros');
    var button = document.getElementById('toggleButton');
    
    if (listaLivros.classList.contains('compact')) {
        listaLivros.classList.remove('compact');
        button.textContent = 'Mostrar menos';
    } else {
        listaLivros.classList.add('compact');
        button.textContent = 'Mostrar Mais';
    }
    
    // Posiciona o botão no canto direito superior da div
    button.style.top = '20px';
    button.style.right = '20px';
}
function showAlert(message, className) {
    var alert = document.getElementById('alert');
    alert.textContent = message;
    alert.className = 'alert ' + className;
    alert.style.display = 'block';

    // Ocultar o alerta após 2 segundos
    setTimeout(function() {
        alert.style.display = 'none';
    }, 2000);
}

// Função para atualizar a posição do alerta conforme o usuário rola a página
window.addEventListener('scroll', function() {
    var alert = document.getElementById('alert');
    alert.style.top = (window.scrollY || window.pageYOffset) + 'px';
});
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form');
    const loading = document.getElementById('loading');

    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            loading.style.display = 'block';

            // Esconde a tela de carregamento após 10 segundos
            setTimeout(function() {
                loading.style.display = 'none';
            }, 100);

            // Permite a submissão do formulário
            event.target.submit();
        });
    });

    // Para capturar erros de resposta HTTP
    window.addEventListener('error', function() {
        loading.style.display = 'none';
    });

    // Esconde a tela de carregamento após a página carregar completamente
    window.addEventListener('load', function() {
        loading.style.display = 'none';
    });
});
