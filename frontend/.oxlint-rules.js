export default {
  meta: { name: "project" },
  rules: {
    "require-arrow-functions": {
      meta: {
        type: "suggestion",
        schema: [],
        messages: { requireArrow: "Use an arrow function instead." },
      },
      create: (context) => ({
        "FunctionDeclaration, FunctionExpression": (node) => {
          const parent = node.parent;

          if (
            node.generator ||
            parent.type === "MethodDefinition" ||
            (parent.type === "Property" && (parent.method || parent.kind !== "init"))
          ) {
            return;
          }

          context.report({ node, messageId: "requireArrow" });
        },
      }),
    },
  },
};
