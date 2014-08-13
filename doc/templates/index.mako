<!doctype html>

<html>

<head>
    <title>Storage Model</title>
    <style>
        body {
            background: #ddd;
            overflow: hidden;
        }
        #left {
            position: fixed;
            top: 0;
            left: 0;
            width: 25%;
            overflow: auto;
        }
        ul {
            list-style: none;
            font-family: Arial, Helvetica, sans-serif;
            font-size: 1em;
            line-height: 1.5;
            padding: 0 0 0 20px;
        }
        ul li a {
            color: #058;
            text-decoration: none;
        }
        iframe {
            position: absolute;
            top: 0;
            left: 25%;
            width: 75%;
            height: 100%;
            border: none;
            border-left: 1px solid #666;
        }
    </style>
</head>

<body>
    <div id="left">
        <ul>
            % for module in modules:
                <li><a href="${module.replace('.', '/')}/index.html" target="main">${module}</a></li>
            % endfor
        </ul>
    </div>
    <iframe src="infi/storagemodel/index.html" name="main">
    </iframe>
</body>

</html>