# Publicar el laboratorio por HTTPS

La app escucha solo `127.0.0.1:8765` en el host por defecto. Esto evita la exposición pública accidental del puerto de aplicación.

## Si tu proxy HTTPS es Nginx

**Ejemplo conceptual** dentro de la configuración del subdominio que ya administras:

```nginx
location / {
    proxy_pass http://127.0.0.1:8765;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 3600s;
}
```

La configuración TLS, dominio, DNS y certificados depende de tu infraestructura existente. Si Nginx también está en un contenedor, `127.0.0.1` referirá a ese **contenedor**, no al host; debes conectar ambos servicios por una red Docker privada o configurar una ruta específica hacia el host. No cambies los puertos 80/443 de tus servicios actuales sin revisar su uso.

Verifica el acceso desde otra red mediante `https://<tu-subdominio>` y comprueba que el estado muestre `CONECTADO`. Los navegadores exigen interacción del usuario para habilitar audio de alertas.

## Control de acceso recomendado

Un aula usa código aleatorio, pero no ofrece por sí sola los controles de seguridad de un campus virtual. Para dar acceso público, usa HTTPS, limitación de peticiones en el proxy, firewall y supervisa las conexiones. Considera poner un acceso adicional al subdominio, sin almacenar datos médicos reales.
