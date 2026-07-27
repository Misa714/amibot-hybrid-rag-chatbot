// Chat Biblioteca Universitaria - Producción Híbrida
// Corrige: D.5/D.6 (XSS), F.5 (texto del botón), F.7 (sonido configurable)
(function() {
    const sesionId = sessionStorage.getItem("chatbot_sesionId") || "user_" + Math.random().toString(36).substring(7);
    sessionStorage.setItem("chatbot_sesionId", sesionId);

    const API_URL = (
        window.location.protocol === 'file:' ||
        !window.location.hostname ||
        window.location.hostname === 'localhost' ||
        window.location.hostname === '127.0.0.1'
    )
        ? 'http://127.0.0.1:8000'
        : (window.location.href.includes('catalogo.example.edu') && !window.location.port
            ? '/chat-api'
            : 'https://catalogo.example.edu/chat-api');

    const CHATBOT_API_KEY = 'CHANGE_ME_IN_PRODUCTION';

    // Función de sanitización para prevenir XSS (corrige D.5/D.6)
    function sanitizarHTML(texto) {
        const div = document.createElement('div');
        div.textContent = texto;
        return div.innerHTML;
    }

    // Función para convertir URLs en enlaces clicables (post-sanitización)
    function linkificar(textoSanitizado) {
        return textoSanitizado.replace(
            /(https?:\/\/[^\s<]+)/g,
            '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'
        );
    }

    const style = document.createElement('style');
    style.textContent = `
        #chat-biblio-boton {
            position: fixed; bottom: 60px; right: 30px;
            height: 50px; padding: 0 22px;
            background: linear-gradient(135deg, #4f46e5 0%, #06b6d4 100%); border-radius: 25px;
            display: flex; justify-content: center; align-items: center; gap: 8px;
            cursor: pointer; z-index: 9999;
            box-shadow: 0 10px 25px -5px rgba(79, 70, 229, 0.4), 0 8px 10px -6px rgba(6, 182, 212, 0.2);
            color: white; font-size: 15px; font-weight: 600;
            white-space: nowrap; user-select: none;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        #chat-biblio-boton:hover { transform: translateY(-3px) scale(1.03); box-shadow: 0 15px 30px -5px rgba(79, 70, 229, 0.5); }

        #chat-biblio-ventana {
            position: fixed; bottom: 140px; right: 30px;
            width: 90%; max-width: 390px; height: 560px; max-height: 72vh;
            background: #ffffff; border-radius: 20px;
            box-shadow: 0 25px 50px -12px rgba(15, 23, 42, 0.25);
            display: flex; flex-direction: column; z-index: 10000;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            overflow: hidden; border: 1px solid #e2e8f0;
            opacity: 0; pointer-events: none;
            transform: translateY(25px) scale(0.95);
            transition: opacity 0.25s cubic-bezier(0.25, 1, 0.5, 1), transform 0.25s cubic-bezier(0.25, 1, 0.5, 1);
        }
        #chat-biblio-ventana.activo { opacity: 1; pointer-events: auto; transform: translateY(0) scale(1); }

        #chat-biblio-header {
            background: linear-gradient(135deg, #4f46e5 0%, #06b6d4 100%); color: white; padding: 18px 22px;
            display: flex; justify-content: space-between;
            align-items: center; font-weight: 600; font-size: 16px;
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.15); z-index: 10;
        }
        #chat-biblio-header span:last-child { cursor: pointer; font-size: 18px; opacity: 0.8; transition: opacity 0.2s; }
        #chat-biblio-header span:last-child:hover { opacity: 1; }

        #chat-biblio-mensajes {
            flex: 1; overflow-y: auto; padding: 20px;
            background: #f8fafc;
            display: flex; flex-direction: column; align-items: flex-start; gap: 14px;
            scroll-behavior: smooth;
        }
        #chat-biblio-mensajes::-webkit-scrollbar { width: 6px; }
        #chat-biblio-mensajes::-webkit-scrollbar-track { background: transparent; }
        #chat-biblio-mensajes::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 10px; }
        #chat-biblio-mensajes::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

        .mensaje-usuario {
            align-self: flex-end;
            background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%); color: #ffffff;
            padding: 12px 16px; border-radius: 18px 18px 4px 18px;
            max-width: 82%; word-wrap: break-word; font-size: 14px; line-height: 1.5;
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.2);
        }
        .mensaje-bot {
            align-self: flex-start;
            background-color: #ffffff; color: #1e293b;
            padding: 12px 16px; border-radius: 18px 18px 18px 4px;
            max-width: 82%; word-wrap: break-word; font-size: 14px; line-height: 1.5;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05); border: 1px solid #e2e8f0;
        }
        .mensaje-bot a { color: #4f46e5; text-decoration: none; font-weight: 500; }
        .mensaje-bot a:hover { text-decoration: underline; }

        #chat-biblio-chips-container.suggestion-chips {
            background: transparent; padding: 0; border-radius: 0;
            display: flex; flex-direction: column; align-items: flex-start; gap: 8px;
            width: fit-content; max-width: 90%; margin: 4px 0 10px 0; box-shadow: none;
        }
        .suggestion-chip {
            background: #e0e7ff; color: #3730a3; border: 1px solid #c7d2fe;
            padding: 8px 14px; border-radius: 20px; cursor: pointer; font-size: 13px;
            transition: all 0.2s ease; white-space: nowrap;
            box-shadow: 0 1px 2px rgba(0,0,0,0.03); font-weight: 500;
        }
        .suggestion-chip:hover {
            background: #4f46e5; color: #ffffff; border-color: #4f46e5;
            transform: translateY(-1px); box-shadow: 0 4px 10px rgba(79, 70, 229, 0.25);
        }

        #chat-biblio-input {
            display: flex; padding: 16px; border-top: 1px solid #f1f5f9;
            background: white; gap: 10px; margin-top: auto; align-items: center;
        }
        #chat-biblio-input input {
            flex: 1; padding: 12px 18px; border: 1px solid #e2e8f0; border-radius: 24px;
            outline: none; font-size: 14px; background: #f8fafc; color: #1e293b; transition: all 0.2s;
        }
        #chat-biblio-input input::placeholder { color: #94a3b8; }
        #chat-biblio-input input:focus {
            border-color: #4f46e5; background: white; box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15);
        }
        #chat-biblio-input button {
            background: linear-gradient(135deg, #4f46e5 0%, #06b6d4 100%); color: white; border: none; padding: 0 20px;
            height: 44px; border-radius: 22px; cursor: pointer; font-size: 14px; font-weight: 600;
            transition: all 0.2s; display: flex; justify-content: center; align-items: center;
        }
        #chat-biblio-input button:hover {
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3); transform: translateY(-1px);
        }

        .btn-cargando { position: relative; pointer-events: none; opacity: 0.8; }
        .btn-cargando::before {
            content: ""; position: absolute; left: 15px; top: 50%; transform: translateY(-50%);
            width: 16px; height: 16px; border: 2px solid transparent; border-top-color: #ffffff;
            border-radius: 50%; animation: giro-spinner 0.8s linear infinite;
        }
        @keyframes giro-spinner { to { transform: translateY(-50%) rotate(360deg); } }

        .chat-toast {
            position: absolute; bottom: 80px; left: 50%; transform: translateX(-50%) translateY(20px);
            background: #ef4444; color: white; padding: 10px 20px; border-radius: 20px;
            font-size: 13px; font-weight: 500; box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            opacity: 0; visibility: hidden; transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            z-index: 10001; white-space: nowrap;
        }
        .chat-toast.exito { background: #10b981; }
        .chat-toast.visible { opacity: 1; visibility: visible; transform: translateX(-50%) translateY(0); }

        .typing-indicator {
            display: flex; align-items: center; gap: 4px; padding: 12px 16px;
            background: #ffffff; border-radius: 18px 18px 18px 4px; max-width: 80%;
            align-self: flex-start; box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05); border: 1px solid #e2e8f0;
        }
        .typing-indicator span {
            width: 8px; height: 8px; background: #6366f1; border-radius: 50%;
            animation: bounce 1.4s infinite ease-in-out both;
        }
        .typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
        .typing-indicator span:nth-child(2) { animation-delay: -0.16s; }
        .typing-indicator span:nth-child(3) { animation-delay: 0s; }
        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }

        @media (max-width: 900px) {
            #chat-biblio-ventana { width: calc(100vw - 20px); max-width: 380px; height: 480px; bottom: 120px; right: 10px; }
            #chat-biblio-boton { bottom: 50px; right: 10px; }
        }
        @media (max-width: 480px) {
            #chat-biblio-boton { bottom: 20px; right: 15px; height: 44px; padding: 0 15px; font-size: 14px; border-radius: 22px; }
            #chat-biblio-ventana {
                bottom: 85px; right: 10px;
                width: calc(100vw - 20px); height: calc(100vh - 160px);
                max-width: 380px; border-radius: 16px 16px 0 0;
            }
            #chat-biblio-mensajes { padding: 12px; gap: 10px; }
            .mensaje-usuario, .mensaje-bot { max-width: 90%; font-size: 13px; padding: 10px 14px; }
            #chat-biblio-input { padding: 12px; gap: 8px; }
            #chat-biblio-input input { padding: 10px 14px; font-size: 13px; }
            #chat-biblio-input button { padding: 8px 16px; font-size: 13px; }
            .suggestion-chip { font-size: 12px; padding: 6px 12px; }
        }

        .chat-meta { font-size: 11px; display: block; text-align: right; margin-top: 4px; opacity: 1.0; font-weight: normal; }
        .mensaje-usuario .chat-meta { color: rgba(255, 255, 255, 0.85); }
        .mensaje-bot .chat-meta { color: #64748b; }

        .chat-biblio-mensaje-grupo {
            display: flex;
            flex-direction: column;
            align-self: flex-start;
            width: 100%;
            margin-bottom: 4px;
        }
        .chat-biblio-fila-bot {
            display: flex; align-items: flex-end; gap: 8px; align-self: flex-start; max-width: 85%; margin-bottom: 0px;
        }
        .chat-biblio-avatar {
            width: 30px; height: 30px; border-radius: 50%; background: linear-gradient(135deg, #4f46e5 0%, #06b6d4 100%);
            display: flex; align-items: center; justify-content: center; flex-shrink: 0; box-shadow: 0 2px 6px rgba(79, 70, 229, 0.3);
        }
        .chat-biblio-avatar svg { width: 16px; height: 16px; stroke: #ffffff; }
        .mensaje-bot-con-avatar {
            align-self: flex-start; background-color: #ffffff; color: #1e293b;
            padding: 10px 14px 22px 14px; border-radius: 4px 18px 18px 18px;
            position: relative; box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05); font-size: 14px; line-height: 1.5; max-width: 100%; border: 1px solid #e2e8f0;
        }
        .mensaje-bot-con-avatar a { color: #4f46e5; text-decoration: none; font-weight: 500; }
        .mensaje-bot-con-avatar a:hover { text-decoration: underline; }
        .mensaje-bot-con-avatar .chat-meta-tiempo { position: absolute; bottom: 4px; right: 10px; font-size: 10px; color: #94a3b8; }

        /* Feedback CSS */
        .feedback-container {
            display: flex;
            gap: 12px;
            margin-top: 4px;
            margin-left: 38px;
            align-self: flex-start;
        }
        .feedback-btn {
            background: none;
            border: none;
            cursor: pointer;
            padding: 2px;
            font-size: 14px;
            color: #94a3b8;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .feedback-btn:hover {
            color: #4f46e5;
            transform: scale(1.2);
        }
        .feedback-btn.liked {
            color: #10b981 !important;
            transform: scale(1.15);
        }
        .feedback-btn.liked svg {
            fill: #10b981;
        }
        .feedback-btn.disliked {
            color: #ef4444 !important;
            transform: scale(1.15);
        }
        .feedback-btn.disliked svg {
            fill: #ef4444;
        }
        /* Formulario de comentario en dislike */
        .feedback-comment-form {
            display: flex;
            flex-direction: column;
            gap: 6px;
            margin-top: 6px;
            margin-left: 38px;
            max-width: 320px;
            animation: fadeIn 0.2s ease;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-4px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .feedback-comment-form textarea {
            font-family: inherit;
            font-size: 12px;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            padding: 8px 10px;
            resize: none;
            outline: none;
            min-height: 42px;
            transition: border-color 0.2s;
        }
        .feedback-comment-form textarea:focus {
            border-color: #4f46e5;
        }
        .feedback-comment-form button {
            align-self: flex-end;
            background: #4f46e5;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 5px 14px;
            font-size: 11px;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.2s;
        }
        .feedback-comment-form button:hover {
            background: #4338ca;
        }
        .feedback-thanks {
            font-size: 11px;
            color: #64748b;
            margin-left: 38px;
            margin-top: 4px;
            animation: fadeIn 0.2s ease;
        }
    `;
    document.head.appendChild(style);

    const ventana = document.createElement('div');
    ventana.id = 'chat-biblio-ventana';
    ventana.innerHTML = '<div id="chat-biblio-header"><span>AmiBot — Asistente RAG</span><span id="chat-biblio-cerrar" style="cursor:pointer">✕</span></div><div id="chat-biblio-mensajes"><div class="mensaje-bot">Hola. Soy AmiBot, tu asistente inteligente de la Biblioteca. ¿En qué te puedo ayudar hoy?</div><div id="chat-biblio-chips-container" class="suggestion-chips"></div><div id="formulario-humano" style="display:none; padding:10px;"><div style="margin-bottom:15px; font-size:14px; color:#333;">Déjanos tu consulta y te responderemos a la brevedad.</div><input type="text" id="rut" placeholder="Identificador / RUT (ej: 123456789)" required style="width:100%; padding:10px; margin-bottom:8px; border:1px solid #ddd; border-radius:8px; font-size:14px;"><input type="email" id="correo" placeholder="Correo de contacto" required style="width:100%; padding:10px; margin-bottom:8px; border:1px solid #ddd; border-radius:8px; font-size:14px;"><textarea id="pregunta-humano" placeholder="Escribe tu consulta aquí..." required style="width:100%; height:80px; padding:10px; margin-bottom:8px; border:1px solid #ddd; border-radius:8px; font-size:14px; resize:none;"></textarea><button onclick="enviarConsultaHumano()" style="width:100%; background:linear-gradient(135deg, #4f46e5 0%, #06b6d4 100%); color:white; border:none; padding:12px; border-radius:8px; cursor:pointer; font-size:14px; font-weight:600;">Enviar consulta</button><button onclick="volverAlChat()" style="width:100%; background:#e2e8f0; color:#334155; border:none; padding:10px; border-radius:8px; cursor:pointer; font-size:13px; margin-top:5px; font-weight:500;">Volver al chat</button></div></div><div id="chat-biblio-input"><input type="text" id="chat-input" placeholder="Escribe tu pregunta..."><button id="chat-enviar">Enviar</button></div>';
    document.body.appendChild(ventana);

    document.getElementById('chat-biblio-cerrar').addEventListener('click', function() {
        ventana.classList.remove('activo');
    });

    const boton = document.createElement('div');
    boton.id = 'chat-biblio-boton';
    boton.innerHTML = 'AmiBot AI';

    boton.onclick = function() {
        ventana.classList.toggle('activo');
    };
    document.body.appendChild(boton);

    function obtenerFechaHoraActual() {
        const ahora = new Date();
        return ahora.toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit', hour12: false });
    }

    const avatarSVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="3"/><circle cx="8.5" cy="15.5" r="1.5" fill="#ffffff"/><circle cx="15.5" cy="15.5" r="1.5" fill="#ffffff"/><path d="M10 18.5h4"/><path d="M12 3v8"/><circle cx="12" cy="3" r="1.5" fill="#ffffff"/></svg>';

    const enviar = async () => {
        const input = document.getElementById('chat-input');
        const pregunta = input.value.trim();
        if (!pregunta) return;

        const mensajes = document.getElementById('chat-biblio-mensajes');
        const marcaTiempo = obtenerFechaHoraActual();

        // CORRIGE D.5: sanitizar entrada del usuario antes de insertar como HTML
        const preguntaSafe = sanitizarHTML(pregunta);
        const metaSafe = sanitizarHTML(marcaTiempo);

        const msgUsuario = document.createElement('div');
        msgUsuario.className = 'mensaje-usuario';
        msgUsuario.textContent = pregunta;
        const metaSpan = document.createElement('span');
        metaSpan.className = 'chat-meta';
        metaSpan.textContent = marcaTiempo;
        msgUsuario.appendChild(metaSpan);
        mensajes.appendChild(msgUsuario);

        input.value = '';

        const typing = document.createElement('div');
        typing.className = 'typing-indicator';
        typing.innerHTML = '<span></span><span></span><span></span>';
        mensajes.appendChild(typing);
        mensajes.scrollTop = mensajes.scrollHeight;

        try {
            const response = await fetch(`${API_URL}/consultar`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-Chatbot-Token': CHATBOT_API_KEY
                },
                body: JSON.stringify({ pregunta: pregunta, sesion: sesionId })
            });
            const data = await response.json();
            typing.remove();

            // CORRIGE D.6: sanitizar respuesta del bot, luego linkificar URLs
            const respuestaSafe = linkificar(sanitizarHTML(data.respuesta));

            const grupoDiv = document.createElement('div');
            grupoDiv.className = 'chat-biblio-mensaje-grupo';

            const filaBotDiv = document.createElement('div');
            filaBotDiv.className = 'chat-biblio-fila-bot';

            const avatarDiv = document.createElement('div');
            avatarDiv.className = 'chat-biblio-avatar';
            avatarDiv.innerHTML = avatarSVG;

            const msgBotDiv = document.createElement('div');
            msgBotDiv.className = 'mensaje-bot-con-avatar';
            msgBotDiv.innerHTML = respuestaSafe;

            const tiempoSpan = document.createElement('span');
            tiempoSpan.className = 'chat-meta-tiempo';
            tiempoSpan.textContent = marcaTiempo;
            msgBotDiv.appendChild(tiempoSpan);

            filaBotDiv.appendChild(avatarDiv);
            filaBotDiv.appendChild(msgBotDiv);
            grupoDiv.appendChild(filaBotDiv);

            // Agregar botones de feedback si existe ID de consulta válido
            if (data.id && data.id > 0) {
                const feedbackDiv = document.createElement('div');
                feedbackDiv.className = 'feedback-container';

                const likeBtn = document.createElement('button');
                likeBtn.className = 'feedback-btn';
                likeBtn.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" style="transition: fill 0.2s;"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path></svg>';
                likeBtn.title = 'Me sirvió';

                const dislikeBtn = document.createElement('button');
                dislikeBtn.className = 'feedback-btn';
                dislikeBtn.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" style="transition: fill 0.2s;"><path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3"></path></svg>';
                dislikeBtn.title = 'No me sirvió';

                const registrarVoto = async (voto, comentario = null) => {
                    try {
                        const payload = { consulta_id: data.id, voto: voto };
                        if (comentario) payload.comentario = comentario;
                        await fetch(`${API_URL}/feedback`, {
                            method: 'POST',
                            headers: { 
                                'Content-Type': 'application/json',
                                'X-Chatbot-Token': CHATBOT_API_KEY
                            },
                            body: JSON.stringify(payload)
                        });
                        likeBtn.disabled = true;
                        dislikeBtn.disabled = true;
                        if (voto === 'like') {
                            likeBtn.classList.add('liked');
                        } else {
                            dislikeBtn.classList.add('disliked');
                        }
                    } catch (err) {
                        console.error('Error al enviar feedback:', err);
                    }
                };

                likeBtn.onclick = () => registrarVoto('like');
                dislikeBtn.onclick = () => {
                    // Mostrar formulario de comentario opcional
                    const existingForm = grupoDiv.querySelector('.feedback-comment-form');
                    if (existingForm) return; // Ya está visible

                    const formDiv = document.createElement('div');
                    formDiv.className = 'feedback-comment-form';

                    const textarea = document.createElement('textarea');
                    textarea.placeholder = '¿Qué esperabas como respuesta? (opcional)';
                    textarea.maxLength = 300;

                    const btnRow = document.createElement('div');
                    btnRow.style.display = 'flex';
                    btnRow.style.gap = '6px';
                    btnRow.style.justifyContent = 'flex-end';

                    const enviarBtn = document.createElement('button');
                    enviarBtn.textContent = 'Enviar';
                    enviarBtn.onclick = async () => {
                        const comentario = textarea.value.trim() || null;
                        await registrarVoto('dislike', comentario);
                        formDiv.remove();
                        const thanks = document.createElement('div');
                        thanks.className = 'feedback-thanks';
                        thanks.textContent = 'Gracias por tu feedback.';
                        grupoDiv.appendChild(thanks);
                    };

                    const omitirBtn = document.createElement('button');
                    omitirBtn.textContent = 'Omitir';
                    omitirBtn.style.background = '#94a3b8';
                    omitirBtn.onclick = async () => {
                        await registrarVoto('dislike');
                        formDiv.remove();
                        const thanks = document.createElement('div');
                        thanks.className = 'feedback-thanks';
                        thanks.textContent = 'Gracias por tu feedback.';
                        grupoDiv.appendChild(thanks);
                    };

                    btnRow.appendChild(omitirBtn);
                    btnRow.appendChild(enviarBtn);
                    formDiv.appendChild(textarea);
                    formDiv.appendChild(btnRow);
                    grupoDiv.appendChild(formDiv);
                    textarea.focus();
                };

                feedbackDiv.appendChild(likeBtn);
                feedbackDiv.appendChild(dislikeBtn);
                grupoDiv.appendChild(feedbackDiv);
            }

            mensajes.appendChild(grupoDiv);

        } catch (e) {
            typing.remove();
            const errorDiv = document.createElement('div');
            errorDiv.className = 'mensaje-bot';
            errorDiv.textContent = 'Error de conexion con el servidor';
            const errorMeta = document.createElement('span');
            errorMeta.className = 'chat-meta';
            errorMeta.textContent = obtenerFechaHoraActual();
            errorDiv.appendChild(errorMeta);
            mensajes.appendChild(errorDiv);
        }
        mensajes.scrollTop = mensajes.scrollHeight;
    };

    const preguntasSugeridas = [
        "Cual es el horario de la biblioteca?",
        "Clave del WiFi?",
        "Que bases de datos tienen?",
        "Como reservar una sala de tesis?",
        "Cuantos libros puedo pedir?",
        "Consultar con un bibliotecario"
    ];

    const chipsContainer = document.getElementById('chat-biblio-chips-container');
    preguntasSugeridas.forEach(function(pregunta) {
        const chip = document.createElement('span');
        chip.className = 'suggestion-chip';
        chip.textContent = pregunta;
        if (pregunta === "Consultar con un bibliotecario") {
            chip.style.background = "#D97706";
            chip.style.color = "white";
            chip.style.borderColor = "white";
            chip.style.fontWeight = "600";
        }
        chip.addEventListener('click', function(e) {
            e.stopPropagation();
            if (pregunta === "Consultar con un bibliotecario") {
                document.getElementById('chat-biblio-chips-container').style.display = 'none';
                document.getElementById('formulario-humano').style.display = 'block';
                document.getElementById('chat-biblio-input').style.display = 'none';
            } else {
                document.getElementById('chat-input').value = pregunta;
                enviar();
            }
        });
        chipsContainer.appendChild(chip);
    });

    document.getElementById('chat-enviar').addEventListener('click', enviar);
    document.getElementById('chat-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') enviar();
    });

    function validarRut(rut) {
        if (rut.includes('.')) return false;
        rut = rut.replace(/[-\s]/g, '');
        if (rut.length < 7) return false;
        const cuerpo = rut.slice(0, -1);
        const dv = rut.slice(-1).toLowerCase();
        if (!/^\d+$/.test(cuerpo)) return false;
        let suma = 0;
        let multiplo = 2;
        for (let i = cuerpo.length - 1; i >= 0; i--) {
            suma += parseInt(cuerpo[i]) * multiplo;
            multiplo = multiplo < 7 ? multiplo + 1 : 2;
        }
        const dvEsperado = 11 - (suma % 11);
        let dvCalculado;
        if (dvEsperado === 11) dvCalculado = '0';
        else if (dvEsperado === 10) dvCalculado = 'k';
        else dvCalculado = dvEsperado.toString();
        return dv === dvCalculado;
    }

    document.addEventListener('input', function(e) {
        if (e.target && e.target.id === 'rut') {
            let valorLimpio = e.target.value.replace(/[^0-9kK]/g, '');
            e.target.value = valorLimpio.toUpperCase();
        }
    });

    function mostrarNotificacion(mensaje, tipo) {
        tipo = tipo || 'error';
        let toast = document.getElementById('chat-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'chat-toast';
            document.getElementById('chat-biblio-ventana').appendChild(toast);
        }
        toast.className = 'chat-toast ' + tipo + ' visible';
        toast.textContent = mensaje;
        setTimeout(function() { toast.classList.remove('visible'); }, 3500);
    }

    window.enviarConsultaHumano = async function() {
        const rutInput = document.getElementById('rut');
        const correoInput = document.getElementById('correo');
        const preguntaInput = document.getElementById('pregunta-humano');
        const botonEnviar = document.querySelector('#formulario-humano button');

        const rut = rutInput.value.trim();
        const correo = correoInput.value.trim();
        const pregunta = preguntaInput.value.trim();

        [rutInput, correoInput, preguntaInput].forEach(function(input) {
            input.style.transition = 'border-color 0.3s';
            input.style.border = '1px solid #e2e8f0';
        });

        if (!rut || !correo || !pregunta) {
            if (!rut) rutInput.style.border = '2px solid #e74c3c';
            if (!correo) correoInput.style.border = '2px solid #e74c3c';
            if (!pregunta) preguntaInput.style.border = '2px solid #e74c3c';
            mostrarNotificacion('Por favor, completa todos los campos.');
            return;
        }

        if (rut.includes('.')) {
            rutInput.style.border = '2px solid #e74c3c';
            mostrarNotificacion('El RUT no debe llevar puntos.');
            return;
        }

        if (!validarRut(rut)) {
            rutInput.style.border = '2px solid #e74c3c';
            mostrarNotificacion('El RUT ingresado no es válido.');
            return;
        }

        var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(correo)) {
            correoInput.style.border = '2px solid #e74c3c';
            mostrarNotificacion('Ingresa un correo válido.');
            return;
        }

        var textoOriginal = botonEnviar.textContent;
        botonEnviar.textContent = 'Enviando...';
        botonEnviar.style.paddingLeft = '35px';
        botonEnviar.classList.add('btn-cargando');
        botonEnviar.disabled = true;

        try {
            const response = await fetch(`${API_URL}/enviar-consulta`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-Chatbot-Token': CHATBOT_API_KEY
                },
                body: JSON.stringify({ rut: rut, correo: correo, pregunta: pregunta })
            });
            await response.json();

            botonEnviar.classList.remove('btn-cargando');
            botonEnviar.style.paddingLeft = '20px';
            botonEnviar.textContent = '¡Enviado!';
            botonEnviar.style.background = '#27ae60';
            botonEnviar.style.borderColor = '#27ae60';

            mostrarNotificacion('Consulta enviada', 'exito');

            setTimeout(function() {
                rutInput.value = ''; correoInput.value = ''; preguntaInput.value = '';
                botonEnviar.textContent = textoOriginal;
                botonEnviar.disabled = false;
                botonEnviar.style.background = '#1a5276';
                botonEnviar.style.borderColor = 'transparent';
                volverAlChat();
            }, 1800);

        } catch (e) {
            botonEnviar.classList.remove('btn-cargando');
            botonEnviar.style.paddingLeft = '20px';
            botonEnviar.textContent = textoOriginal;
            botonEnviar.disabled = false;
            mostrarNotificacion('Error de conexión. Intenta nuevamente.');
        }
    };

    window.volverAlChat = function() {
        var formHumano = document.getElementById('formulario-humano');
        var chipsContainer = document.getElementById('chat-biblio-chips-container');
        var inputContainer = document.getElementById('chat-biblio-input');

        formHumano.style.opacity = '0';
        setTimeout(function() {
            formHumano.style.display = 'none';
            formHumano.style.opacity = '1';
            chipsContainer.style.display = 'flex';
            inputContainer.style.display = 'flex';
        }, 200);
    };

    console.log('Chat RAG Híbrido con Sanitización XSS Activado');
})();

