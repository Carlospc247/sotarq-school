class EducationQuote extends HTMLElement {
  connectedCallback() {
    this.attachShadow({ mode: 'open' });
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          margin: 1rem 0;
        }
        .quote-container {
          background: rgba(255, 255, 255, 0.1);
          backdrop-filter: blur(10px);
          border-left: 4px solid #818cf8;
          padding: 1rem;
          border-radius: 0 8px 8px 0;
          transition: all 0.3s ease;
        }
        .quote-container:hover {
          background: rgba(255, 255, 255, 0.15);
          transform: translateX(4px);
        }
        .quote-text {
          font-style: italic;
          font-size: 1.125rem;
          line-height: 1.6;
          color: white;
          margin: 0;
        }
        .quote-author {
          font-size: 0.75rem;
          font-weight: bold;
          text-transform: uppercase;
          letter-spacing: 0.1em;
          color: #a5b4fc;
          margin-top: 0.5rem;
        }
      </style>
      <div class="quote-container">
        <p class="quote-text"><slot name="quote"></slot></p>
        <p class="quote-author"><slot name="author"></slot></p>
      </div>
    `;
  }
}

customElements.define('education-quote', EducationQuote);