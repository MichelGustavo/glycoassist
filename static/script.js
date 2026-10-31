const selectPaciente = document.getElementById("select-paciente");
const dadosPaciente = document.getElementById("dados-paciente");
const listaMedicoes = document.getElementById("lista-medicoes");
const listaMedicamentos = document.getElementById("lista-medicamentos");
const listaDocumentos = document.getElementById("lista-documentos");
const inputPdf = document.getElementById("input-pdf");
const chat = document.getElementById("chat");
const formMensagem = document.getElementById("form-mensagem");
const campoMensagem = document.getElementById("campo-mensagem");
const btnEnviar = document.getElementById("btn-enviar");
const btnLimparChat = document.getElementById("btn-limpar-chat");
const botoesSugestao = document.querySelectorAll(".sugestao");

function pacienteSelecionado() {
  const valor = Number(selectPaciente.value);
  return Number.isInteger(valor) && valor > 0 ? valor : null;
}

function escaparVazio(valor, sufixo = "") {
  return valor === null || valor === undefined || valor === ""
    ? "—"
    : `${valor}${sufixo}`;
}

function dataPt(valor) {
  if (!valor) return "—";
  const data = new Date(`${String(valor).slice(0, 10)}T00:00:00`);
  if (Number.isNaN(data.getTime())) return valor;
  return data.toLocaleDateString("pt-BR");
}

function dataHoraPt(valor) {
  if (!valor) return "—";
  const data = new Date(valor);
  if (Number.isNaN(data.getTime())) return valor;
  return data.toLocaleString("pt-BR");
}

function adicionarMensagem(texto, tipo, rotulo) {
  const div = document.createElement("div");
  div.className = `mensagem ${tipo}`;

  if (rotulo) {
    const span = document.createElement("span");
    span.className = "rotulo";
    span.textContent = rotulo;
    div.appendChild(span);
  }

  const corpo = document.createElement("span");
  corpo.textContent = texto;
  div.appendChild(corpo);
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

function travar(travar) {
  campoMensagem.disabled = travar;
  btnEnviar.disabled = travar;
  selectPaciente.disabled = travar;
  botoesSugestao.forEach((botao) => {
    botao.disabled = travar || !pacienteSelecionado();
  });
}

function atualizarSugestoes() {
  const pacienteDisponivel = Boolean(pacienteSelecionado());
  botoesSugestao.forEach((botao) => {
    botao.disabled = !pacienteDisponivel;
  });
}

function verificarSessao(resposta) {
  if (resposta.status === 401) {
    window.location.href = "/login";
    throw new Error("Sua sessão expirou.");
  }
  return resposta;
}

function limparPainel() {
  dadosPaciente.textContent = "";
  listaMedicoes.innerHTML = '<tr><td colspan="4" class="vazio">Selecione um paciente.</td></tr>';
  listaMedicamentos.innerHTML = '<li class="vazio">Selecione um paciente.</li>';
  listaDocumentos.innerHTML = '<li class="vazio">Selecione um paciente.</li>';
}

async function carregarPacientes() {
  limparPainel();
  try {
    const resposta = verificarSessao(await fetch("/api/pacientes"));
    const dados = await resposta.json();

    if (!resposta.ok) {
      throw new Error(dados.erro || "Não foi possível carregar os pacientes.");
    }

    selectPaciente.innerHTML = '<option value="">Selecione...</option>';
    dados.pacientes.forEach((paciente) => {
      const option = document.createElement("option");
      option.value = paciente.id;
      option.textContent = `${paciente.nome} (ID ${paciente.id})`;
      selectPaciente.appendChild(option);
    });

    if (dados.pacientes.length === 0) {
      selectPaciente.innerHTML = '<option value="">Nenhum paciente cadastrado</option>';
    }
  } catch (erro) {
    selectPaciente.innerHTML = '<option value="">Erro ao acessar o banco</option>';
    adicionarMensagem(erro.message, "sistema");
  }
}

function renderizarPaciente(dados) {
  const p = dados.paciente;
  dadosPaciente.innerHTML = "";

  const nome = document.createElement("strong");
  nome.textContent = p.nome;
  const detalhe = document.createElement("span");
  detalhe.textContent = `ID ${p.id} • idade: ${escaparVazio(p.idade)}`;
  dadosPaciente.append(nome, detalhe);

  listaMedicoes.innerHTML = "";
  if (!dados.medicoes.length) {
    listaMedicoes.innerHTML = '<tr><td colspan="4" class="vazio">Nenhuma medição cadastrada.</td></tr>';
  } else {
    dados.medicoes.forEach((m) => {
      const tr = document.createElement("tr");
      const valores = [
        dataPt(m.data),
        escaparVazio(m.glicemia, " mg/dL"),
        escaparVazio(m.hba1c, "%"),
        escaparVazio(m.peso, " kg"),
      ];
      valores.forEach((valor) => {
        const td = document.createElement("td");
        td.textContent = valor;
        tr.appendChild(td);
      });
      listaMedicoes.appendChild(tr);
    });
  }

  listaMedicamentos.innerHTML = "";
  if (!dados.medicamentos.length) {
    listaMedicamentos.innerHTML = '<li class="vazio">Nenhum medicamento cadastrado.</li>';
  } else {
    dados.medicamentos.forEach((med) => {
      const li = document.createElement("li");
      const titulo = document.createElement("strong");
      titulo.textContent = med.nome;
      const detalheMed = document.createElement("span");
      detalheMed.textContent = `${escaparVazio(med.dose)} • início: ${dataPt(med.data_inicio)}${med.data_fim ? ` • fim: ${dataPt(med.data_fim)}` : ""}`;
      li.append(titulo, detalheMed);
      listaMedicamentos.appendChild(li);
    });
  }

  listaDocumentos.innerHTML = "";
  if (!dados.documentos.length) {
    listaDocumentos.innerHTML = '<li class="vazio">Nenhum documento enviado.</li>';
  } else {
    dados.documentos.forEach((doc) => {
      const li = document.createElement("li");
      li.className = "item-documento";
      const informacoes = document.createElement("div");
      informacoes.className = "documento-informacoes";
      const titulo = document.createElement("strong");
      titulo.textContent = doc.nome_arquivo;
      const detalheDoc = document.createElement("span");
      detalheDoc.textContent = dataHoraPt(doc.data_upload);
      informacoes.append(titulo, detalheDoc);

      const botaoExcluir = document.createElement("button");
      botaoExcluir.type = "button";
      botaoExcluir.className = "botao-excluir-documento";
      botaoExcluir.textContent = "Remover";
      botaoExcluir.setAttribute("aria-label", `Remover documento ${doc.nome_arquivo}`);
      botaoExcluir.addEventListener("click", () => excluirDocumento(doc, botaoExcluir));

      li.append(informacoes, botaoExcluir);
      listaDocumentos.appendChild(li);
    });
  }
}

async function excluirDocumento(documento, botao) {
  const pacienteId = pacienteSelecionado();
  if (!pacienteId) return;

  const confirmou = window.confirm(
    `Remover o documento “${documento.nome_arquivo}”? Esta ação não pode ser desfeita.`
  );
  if (!confirmou) return;

  botao.disabled = true;
  try {
    const resposta = verificarSessao(await fetch(
      `/api/pacientes/${pacienteId}/documentos/${documento.id}`,
      { method: "DELETE" }
    ));
    const dados = await resposta.json();
    if (!resposta.ok) throw new Error(dados.erro || "Não foi possível remover o documento.");

    adicionarMensagem(
      dados.aviso || `Documento “${dados.nome_arquivo}” removido. O contexto da conversa foi reiniciado.`,
      "sistema"
    );
    await carregarPaciente();
  } catch (erro) {
    botao.disabled = false;
    adicionarMensagem(erro.message, "sistema");
  }
}

async function carregarPaciente() {
  const pacienteId = pacienteSelecionado();
  if (!pacienteId) {
    limparPainel();
    return;
  }

  try {
    const resposta = verificarSessao(await fetch(`/api/pacientes/${pacienteId}`));
    const dados = await resposta.json();
    if (!resposta.ok) throw new Error(dados.erro || "Erro ao carregar paciente.");
    renderizarPaciente(dados);
  } catch (erro) {
    adicionarMensagem(erro.message, "sistema");
  }
}

async function enviarMensagem(mensagem) {
  const pacienteId = pacienteSelecionado();
  if (!pacienteId) {
    adicionarMensagem("Selecione um paciente antes de perguntar.", "sistema");
    return;
  }

  adicionarMensagem(mensagem, "usuario", "Você");
  travar(true);
  const carregando = adicionarMensagem("Consultando banco e documentos...", "sistema");

  try {
    const respostaHttp = verificarSessao(await fetch("/api/mensagem", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ paciente_id: pacienteId, mensagem }),
    }));
    const dados = await respostaHttp.json();
    carregando.remove();

    if (!respostaHttp.ok) throw new Error(dados.erro || "Erro ao gerar resposta.");
    adicionarMensagem(dados.resposta, "assistente", "Assistente");
  } catch (erro) {
    carregando.remove();
    adicionarMensagem(erro.message, "sistema");
  } finally {
    travar(false);
    campoMensagem.focus();
  }
}

async function enviarPdf(arquivo) {
  const pacienteId = pacienteSelecionado();
  if (!pacienteId) {
    adicionarMensagem("Selecione um paciente antes de enviar um PDF.", "sistema");
    return;
  }

  const formData = new FormData();
  formData.append("arquivo", arquivo);
  formData.append("paciente_id", pacienteId);

  travar(true);
  const carregando = adicionarMensagem(`Enviando ${arquivo.name}...`, "sistema");

  try {
    const resposta = verificarSessao(await fetch("/api/upload", { method: "POST", body: formData }));
    const dados = await resposta.json();
    carregando.remove();

    if (!resposta.ok) throw new Error(dados.erro || "Não foi possível enviar o arquivo.");
    adicionarMensagem(`PDF “${dados.documento.nome_arquivo}” vinculado ao paciente e registrado no banco.`, "sistema");
    await carregarPaciente();
  } catch (erro) {
    carregando.remove();
    adicionarMensagem(erro.message, "sistema");
  } finally {
    travar(false);
  }
}

formMensagem.addEventListener("submit", (evento) => {
  evento.preventDefault();
  const mensagem = campoMensagem.value.trim();
  if (!mensagem) return;
  campoMensagem.value = "";
  enviarMensagem(mensagem);
});

selectPaciente.addEventListener("change", async () => {
  await carregarPaciente();
  atualizarSugestoes();
  chat.innerHTML = "";
  if (pacienteSelecionado()) {
    adicionarMensagem("Tudo certo. Escolha uma sugestão ou escreva sua própria pergunta.", "sistema");
    campoMensagem.focus();
  } else {
    adicionarMensagem("Selecione um paciente para começar.", "sistema");
  }
});

botoesSugestao.forEach((botao) => {
  botao.addEventListener("click", () => {
    const pergunta = botao.dataset.pergunta;
    if (pergunta && pacienteSelecionado()) enviarMensagem(pergunta);
  });
});

inputPdf.addEventListener("change", () => {
  const arquivo = inputPdf.files[0];
  if (arquivo) enviarPdf(arquivo);
  inputPdf.value = "";
});

btnLimparChat.addEventListener("click", async () => {
  const pacienteId = pacienteSelecionado();
  if (!pacienteId) {
    chat.innerHTML = "";
    adicionarMensagem("Selecione um paciente para começar.", "sistema");
    return;
  }

  try {
    verificarSessao(await fetch("/api/chat/limpar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ paciente_id: pacienteId }),
    }));
  } finally {
    chat.innerHTML = "";
    adicionarMensagem("Conversa limpa. Os dados do paciente permanecem no banco.", "sistema");
  }
});

atualizarSugestoes();
carregarPacientes();
