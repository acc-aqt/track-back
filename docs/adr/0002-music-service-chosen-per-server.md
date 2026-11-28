# Music Service chosen per server, with a per-Game-Session override

The Host used to pick the Music Service for every Game Session, even though only the Server Operator knows which services this machine can use. Hosts could pick one that didn't work, such as Apple Music on a non-Mac server or Spotify without credentials, and only found out when creating the Game Session failed. Now the Server Operator chooses the Music Service when starting the server, with `--music-service` or `MUSIC_SERVICE`, falling back to Apple Music on macOS and Spotify elsewhere. The server refuses to start if the chosen service can't work. A Host may still switch the Music Service for their own Game Session, but only among the services available on the server.

We considered a server-wide setting that a Player could change from the Web UI, and rejected it: the server has no authentication, so any Player on the LAN could change the Music Service for everyone.

## Consequences

- `POST /create` treats `music_service_type` as optional and falls back to the server's Music Service. A service that isn't available gets 400.
- The Mock Music Service is only available when the server was started with it, so it can't be picked on a production server. Scripts that created Mock Game Sessions on a server started without `--music-service mock` now get 400.
- `POST /create` refuses Spotify with 400: a Spotify Game Session needs the Host's Spotify login, so it is created through `/spotify-login` instead.
