---
    permalink: /about/officers
    title: Club Officers
---

## Meet the Board

GREEN is led by a passionate group of UC Davis students committed to advancing agricultural technology and sustainability. Our board organizes events, manages club operations, and represents our community.

Interested in joining the board? Reach out to us at [greenucd@gmail.com](mailto:greenucd@gmail.com) or follow us on [Instagram](https://www.instagram.com/green.ucd/).

## Current Board of Directors
<div>
  {% for category in site.data.positions %}
    <h3>{{ category.title }}</h3>
    <div class="row is-flex">
      {% for position in category.positions %}
        {% for officer_id in position.officers %}
          {% assign officer = site.data.officers[officer_id] %}
          <div class="col-lg-2 col-md-3 col-sm-4 col-xs-6 officer-card">
            <img height="115" width="115" alt="" src="/images/leaders/{{ officer.photo | default: 'beaver.jpg'}}"/>
            <div class="officer-info">
              <strong class="officer-name">{{ officer.name }}</strong>
              <span class="officer-title">{{ position.title }}</span>
            </div>
            {% if officer.bio %}<p><small>{{ officer.bio }}</small></p>{% endif %}
          </div>
        {% endfor %}
      {% endfor %}
    </div>
  {% endfor %}
</div>

## Contact Us

For general questions about GREEN, email [greenucd@gmail.com](mailto:greenucd@gmail.com).

Follow us on [Instagram @green.ucd](https://www.instagram.com/green.ucd/) or join our [Discord](https://discord.com/invite/5krgBsWp3r).
