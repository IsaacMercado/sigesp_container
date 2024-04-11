<?php

$file = "/home/isaac/projects/sigesp/sob/sigesp_sob_r_reportepartidasobra.php";
$code = file_get_contents($file);

$code = preg_replace(["/<\? /", "/<\?[\r\n]/"], ["<?php ", "<?php\n"], $code);

file_put_contents("test.php", $code);
