{
  description = "Cloud Scythe Labs brand assets: font build toolchain";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          packages = [
            (pkgs.python3.withPackages (ps:
              [
                ps.fonttools
                ps.ufo2ft
                ps.fontmake
                ps.ufolib2
                ps.compreffor
                ps.skia-pathops
                ps.ufonormalizer
                ps.pillow
              ]
              ++ ps.fonttools.optional-dependencies.woff))
            pkgs.fontforge
            pkgs.gnumake
          ];
          # mkShell exports SOURCE_DATE_EPOCH=315532800; build.py would stamp it
          # into head.modified and the binaries would differ from non-Nix builds.
          shellHook = ''
            unset SOURCE_DATE_EPOCH
          '';
        };
      });
    };
}
