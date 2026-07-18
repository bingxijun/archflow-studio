# Third-party boundary

The bundled CAD bridge, MCP stdio server, SketchUp Ruby bridge, deployment scripts, validators, and generators are ArchFlow source code under Apache-2.0. The package does not bundle a third-party SketchUp MCP implementation.

ArchFlow interoperates with user-supplied proprietary applications through their installed COM or Ruby automation APIs. AutoCAD, AutoLISP, Autodesk, SketchUp, Trimble, BricsCAD, ZWCAD, GstarCAD, Windows, and Codex remain products or trademarks of their respective owners. Users must supply valid application licenses.

Run `scripts/validate_skill_package.py` before distribution. It rejects unsupported SkillHub file types and verifies that the published Ruby text sources reproducibly generate the RBZ SHA-256 locked in `assets/integration-lock.json`.
