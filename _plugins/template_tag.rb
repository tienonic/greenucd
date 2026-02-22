module Jekyll
  class TemplateTag < Liquid::Block
    def initialize(tag_name, markup, tokens)
      super
      parts = markup.strip.split(/\s+/, 2)
      @template_file = parts[0]
      @params = {}
      if parts[1]
        parts[1].scan(/(\w+):\s*"([^"]*)"/) do |key, value|
          @params[key] = value
        end
      end
    end

    def render(context)
      content = super
      site = context.registers[:site]
      template_path = File.join(site.source, '_templates', @template_file)
      return "Template not found: #{@template_file}" unless File.exist?(template_path)

      template_src = File.read(template_path)
      context.stack do
        context['template'] = @params.merge('content' => content)
        Liquid::Template.parse(template_src).render(context)
      end
    end
  end
end

Liquid::Template.register_tag('template', Jekyll::TemplateTag)
