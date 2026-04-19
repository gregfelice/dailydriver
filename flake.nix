{
  description = "Visual keyboard shortcut configuration for GNOME/Wayland";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        python = pkgs.python311;
        pythonPackages = python.pkgs;
      in
      {
        packages.default = pythonPackages.buildPythonApplication {
          pname = "dailydriver";
          version = "0.2.0";
          format = "pyproject";

          src = ./.;

          nativeBuildInputs = with pkgs; [
            meson
            ninja
            pkg-config
            gobject-introspection
            wrapGAppsHook4
            desktop-file-utils
          ];

          buildInputs = with pkgs; [
            gtk4
            libadwaita
            dconf
            glib
          ];

          propagatedBuildInputs = with pythonPackages; [
            pygobject3
            pydantic
            tomli-w
          ];

          # Meson build is handled by buildPythonApplication via pyproject.toml
          # but we need to ensure GSettings schemas are compiled
          postInstall = ''
            glib-compile-schemas $out/share/glib-2.0/schemas
          '';

          meta = with pkgs.lib; {
            description = "Visual keyboard configuration for GNOME";
            homepage = "https://github.com/gregfelice/dailydriver";
            license = licenses.gpl3Plus;
            platforms = platforms.linux;
          };
        };

        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            python
            pythonPackages.pygobject3
            pythonPackages.pydantic
            pythonPackages.tomli-w
            gtk4
            libadwaita
            gobject-introspection
            meson
            ninja
            pkg-config
          ];
        };
      }
    );
}
