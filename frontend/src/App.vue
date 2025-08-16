<template>
  <v-app>
    <!-- Navigation Bar -->
    <v-app-bar app color="primary" dark>
      <v-app-bar-title>
        <v-icon icon="mdi-dna" class="mr-2" />
        Kidney Genetics DB
      </v-app-bar-title>

      <v-spacer />

      <v-btn text to="/" variant="text"> Home </v-btn>
      <v-btn text to="/genes" variant="text"> Genes </v-btn>
      <v-btn text to="/about" variant="text"> About </v-btn>
    </v-app-bar>

    <!-- Main Content -->
    <v-main>
      <router-view />
    </v-main>

    <!-- Footer -->
    <v-footer app color="primary" dark>
      <v-col class="text-center" cols="12">
        {{ new Date().getFullYear() }} — Kidney Genetics Database
      </v-col>
    </v-footer>
  </v-app>
</template>

<script setup>
// No additional logic needed for app shell
</script>

<style>
/* Global styles if needed */
</style>
