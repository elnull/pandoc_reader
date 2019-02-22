import logging
import subprocess

from pelican import signals
from pelican.readers import BaseReader
from pelican.utils import pelican_open
import urllib.parse


try:
    import yaml
except ImportError:
    yaml = None
    logging.warning("YAML is not installed; the YAML reader will not work.")


class PandocReader(BaseReader):
    enabled = True
    file_extensions = ['md', 'markdown', 'mkd', 'mdown']

    def _get_meta_and_content(self, text):
        metadata = {}

        use_YAML = text[0] == '---' and yaml is not None
        if use_YAML:
            # Load the data we need to parse
            to_parse = []
            for i, line in enumerate(text[1:]):
                # When we find a terminator (`---` or `...`), stop.
                if line in ('---', '...'):
                    # Do not include the terminator itself.
                    break

                # Otherwise, just keep adding the lines to the parseable.
                to_parse.append(line)

            parsed = yaml.load("\n".join(to_parse))

            # Postprocess to make the data usable by Pelican.
            for k in parsed:
                name, value = k.lower(), parsed[k]
                metadata[name] = self.process_metadata(name, value)

            # Return the text entirely.
            content = "\n".join(text)

        else:
            for i, line in enumerate(text):
                kv = line.split(':', 1)
                if len(kv) == 2:
                    name, value = kv[0].lower(), kv[1].strip()
                    metadata[name] = self.process_metadata(name, value)
                else:
                    content = "\n".join(text[i:])
                    break

        return metadata, content

    def read(self, filename):
        with pelican_open(filename) as fp:
            text = list(fp.splitlines())

        metadata, content = self._get_meta_and_content(text)

        extra_args = self.settings.get('PANDOC_ARGS', [])
        extensions = self.settings.get('PANDOC_EXTENSIONS', '')
        if isinstance(extensions, list):
            extensions = ''.join(extensions)

        pandoc_cmd = ["pandoc", "--from=markdown" + extensions, "--to=html5"]
        pandoc_cmd.extend(extra_args)

        proc = subprocess.Popen(pandoc_cmd,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE)

        output = proc.communicate(content.encode('utf-8'))[0].decode('utf-8')
        status = proc.wait()
        if status:
            raise subprocess.CalledProcessError(status, pandoc_cmd)

        return output, metadata


def add_reader(readers):
    for ext in PandocReader.file_extensions:
        readers.reader_classes[ext] = PandocReader


def register():
    signals.readers_init.connect(add_reader)
