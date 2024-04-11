<?php
// Cargar el autoloader del PHP-Parser
require_once 'vendor/autoload.php';

// Crear un objeto parser
$parser = new PhpParser\Parser\Php5(new PhpParser\Lexer);

// Crear un objeto printer
$printer = new PhpParser\PrettyPrinter\Standard;

// Crear un objeto traverser
$traverser = new PhpParser\NodeTraverser;

// Crear un objeto visitor
$visitor = new class extends PhpParser\NodeVisitorAbstract {
    // Este método se ejecuta cuando se encuentra un nodo
    public function enterNode(PhpParser\Node $node)
    {
        // Si el nodo es una llamada a una función
        if ($node instanceof PhpParser\Node\Expr\FuncCall) {
            // Recorrer los argumentos de la llamada
            foreach ($node->args as $arg) {
                // Si el argumento tiene el operador &
                if ($arg->byRef) {
                    // Eliminar el operador &
                    $arg->byRef = false;
                    // Mostrar un mensaje de aviso
                    echo "Se ha encontrado y eliminado un & en la llamada a la función " . $node->name . "\n";
                }
            }
        }
    }
};

// Añadir el visitor al traverser
$traverser->addVisitor($visitor);

$filepath = "/mnt/c/laragon/www/sigesp/apr/class_folder/class_sigesp_int_spg.php";
$file = fopen($filepath, "r");
$content = fread($file, filesize($filepath));
fclose($file);

$content = iconv("ISO-8859-1", "UTF-8", $content);

try {
    // Analizar el código con el parser
    $stmts = $parser->parse($content);
    // Recorrer los nodos con el traverser
    $stmts = $traverser->traverse($stmts);
    // Imprimir el código modificado con el printer
    $newCode = $printer->prettyPrintFile($stmts);
    // Escribir el nuevo código en el archivo
    $file = fopen($filepath, "w");
    fwrite($file, $newCode);
    fclose($file);
    // Mostrar un mensaje de éxito
    echo "Se ha procesado correctamente el archivo " . $file . "\n";
} catch (PhpParser\Error $e) {
    // Mostrar un mensaje de error
    echo "Se ha producido un error al procesar el archivo " . $file . ": " . $e->getMessage() . "\n";
}

// // Abrir el directorio
// if ($handle = opendir($dir)) {
//     // Leer los archivos del directorio
//     while (false !== ($file = readdir($handle))) {
//         // Si el archivo tiene extensión .php
//         if (pathinfo($file, PATHINFO_EXTENSION) == "php") {
//             // Leer el contenido del archivo
//             $code = file_get_contents($dir . "/" . $file);
//             try {
//                 // Analizar el código con el parser
//                 $stmts = $parser->parse($code);
//                 // Recorrer los nodos con el traverser
//                 $stmts = $traverser->traverse($stmts);
//                 // Imprimir el código modificado con el printer
//                 $newCode = $printer->prettyPrintFile($stmts);
//                 // Escribir el nuevo código en el archivo
//                 file_put_contents($dir . "/" . $file, $newCode);
//                 // Mostrar un mensaje de éxito
//                 echo "Se ha procesado correctamente el archivo " . $file . "\n";
//             } catch (PhpParser\Error $e) {
//                 // Mostrar un mensaje de error
//                 echo "Se ha producido un error al procesar el archivo " . $file . ": " . $e->getMessage() . "\n";
//             }
//         }
//     }
//     // Cerrar el directorio
//     closedir($handle);
// }
?>