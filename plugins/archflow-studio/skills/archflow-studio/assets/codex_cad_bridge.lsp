;;; codex_cad_bridge.lsp
;;; SPDX-FileCopyrightText: 2026 OHDESIGN
;;; SPDX-License-Identifier: Apache-2.0

(vl-load-com)

(defun codex-json-escape (s / i c out)
  (setq s (if s (vl-princ-to-string s) ""))
  (setq i 1)
  (setq out "")
  (while (<= i (strlen s))
    (setq c (substr s i 1))
    (cond
      ((= c "\\") (setq out (strcat out "\\\\")))
      ((= c "\"") (setq out (strcat out "\\\"")))
      ((= c "\n") (setq out (strcat out "\\n")))
      ((= c "\r") (setq out (strcat out "\\r")))
      (T (setq out (strcat out c)))
    )
    (setq i (1+ i))
  )
  out
)

(defun codex-json-string (s)
  (strcat "\"" (codex-json-escape s) "\"")
)

(defun codex-inc-count (key counts / pair result found)
  (setq result '())
  (setq found nil)
  (foreach pair counts
    (if (= (car pair) key)
      (progn
        (setq result (cons (cons key (1+ (cdr pair))) result))
        (setq found T)
      )
      (setq result (cons pair result))
    )
  )
  (if found
    (reverse result)
    (cons (cons key 1) counts)
  )
)

(defun codex-layer-names (/ item names)
  (setq names '())
  (setq item (tblnext "LAYER" T))
  (while item
    (setq names (cons (cdr (assoc 2 item)) names))
    (setq item (tblnext "LAYER"))
  )
  (reverse names)
)

(defun codex-entity-counts (/ ss i ent typ counts)
  (setq counts '())
  (setq ss (ssget "_X"))
  (if ss
    (progn
      (setq i 0)
      (while (< i (sslength ss))
        (setq ent (entget (ssname ss i)))
        (setq typ (cdr (assoc 0 ent)))
        (setq counts (codex-inc-count typ counts))
        (setq i (1+ i))
      )
    )
  )
  counts
)

(defun codex-temp-json-path ()
  (strcat (getenv "TEMP") "\\codex-cad-context.json")
)

(defun codex-write-json (path / f layers counts first)
  (setq f (open path "w"))
  (if (not f)
    (progn
      (princ (strcat "\nCodex CAD: cannot write " path))
      nil
    )
    (progn
      (write-line "{" f)
      (write-line (strcat "  \"drawingName\": " (codex-json-string (getvar "DWGNAME")) ",") f)
      (write-line (strcat "  \"drawingPath\": " (codex-json-string (getvar "DWGPREFIX")) ",") f)
      (write-line (strcat "  \"cadVersion\": " (codex-json-string (getvar "ACADVER")) ",") f)
      (write-line "  \"layers\": [" f)
      (setq layers (codex-layer-names))
      (setq first T)
      (foreach layer layers
        (if first
          (setq first nil)
          (write-line "," f)
        )
        (princ (strcat "    " (codex-json-string layer)) f)
      )
      (write-line "" f)
      (write-line "  ]," f)
      (write-line "  \"entityCounts\": [" f)
      (setq counts (codex-entity-counts))
      (setq first T)
      (foreach pair counts
        (if first
          (setq first nil)
          (write-line "," f)
        )
        (princ (strcat "    {\"type\": " (codex-json-string (car pair)) ", \"count\": " (itoa (cdr pair)) "}") f)
      )
      (write-line "" f)
      (write-line "  ]" f)
      (write-line "}" f)
      (close f)
      path
    )
  )
)

(defun codex-export (path)
  (if (not path)
    (setq path (codex-temp-json-path))
  )
  (codex-write-json path)
)

(defun c:CODEXEXPORT (/ path result)
  (setq path (getfiled "Save Codex CAD context JSON" (codex-temp-json-path) "json" 1))
  (if path
    (progn
      (setq result (codex-write-json path))
      (if result
        (princ (strcat "\nCodex CAD exported: " result))
      )
    )
  )
  (princ)
)

(defun c:CODEXHELP ()
  (princ "\nCodex CAD helper loaded.")
  (princ "\nCommands:")
  (princ "\n  CODEXHELP   - Show this help.")
  (princ "\n  CODEXEXPORT - Export drawing context JSON.")
  (princ "\nFunction:")
  (princ "\n  (codex-export \"C:/temp/codex-cad-context.json\")")
  (princ "\nOfficial website: https://archflow.best")
  (princ)
)

(princ "\nCodex CAD helper loaded. Official website: https://archflow.best. Run CODEXHELP.")
(princ)
